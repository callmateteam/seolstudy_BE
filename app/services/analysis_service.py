import asyncio
import json
import logging
import random

from fastapi import HTTPException, status
from openai import AsyncOpenAI
from prisma import Json, Prisma

from app.core.config import settings
from app.services.upload_service import _key_from_url, generate_presigned_url

logger = logging.getLogger(__name__)

_openai_client: AsyncOpenAI | None = None


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def _is_mock_mode() -> bool:
    return settings.APP_ENV == "test" or not settings.OPENAI_API_KEY


# ---------- trigger / status / retry ----------

async def trigger_analysis(db: Prisma, submission_id: str):
    submission = await db.tasksubmission.find_unique(where={"id": submission_id})
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ANALYSIS_003", "message": "제출물을 찾을 수 없습니다"},
        )

    existing = await db.aianalysis.find_unique(where={"submissionId": submission_id})
    if existing and existing.status in ("PROCESSING", "COMPLETED"):
        return {"analysisId": existing.id, "status": existing.status}

    if existing:
        await db.aianalysis.update(
            where={"id": existing.id},
            data={"status": "PROCESSING"},
        )
        analysis_id = existing.id
    else:
        analysis = await db.aianalysis.create(
            data={
                "submission": {"connect": {"id": submission_id}},
                "status": "PROCESSING",
            }
        )
        analysis_id = analysis.id

    await db.task.update(
        where={"id": submission.taskId},
        data={"status": "ANALYZING"},
    )

    return {"analysisId": analysis_id, "status": "PROCESSING"}


async def get_analysis(db: Prisma, submission_id: str):
    analysis = await db.aianalysis.find_unique(where={"submissionId": submission_id})
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ANALYSIS_003", "message": "분석 결과를 찾을 수 없습니다"},
        )
    return analysis


async def get_analysis_status(db: Prisma, submission_id: str):
    analysis = await db.aianalysis.find_unique(where={"submissionId": submission_id})
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ANALYSIS_003", "message": "분석 결과를 찾을 수 없습니다"},
        )
    return {"id": analysis.id, "submissionId": submission_id, "status": analysis.status}


async def retry_analysis(db: Prisma, submission_id: str):
    analysis = await db.aianalysis.find_unique(where={"submissionId": submission_id})
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ANALYSIS_003", "message": "분석 결과를 찾을 수 없습니다"},
        )

    if analysis.status != "FAILED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ANALYSIS_001", "message": "실패 상태의 분석만 재시도 가능합니다"},
        )

    await db.aianalysis.update(
        where={"id": analysis.id},
        data={"status": "PROCESSING", "retryCount": analysis.retryCount + 1},
    )

    return {"analysisId": analysis.id, "status": "PROCESSING"}


# ---------- GPT-4o Vision 분석 ----------

ANALYSIS_JSON_SCHEMA = """{
  "densityScore": (0~100 정수, 전체 학습 밀도),
  "signalLight": ("GREEN" | "YELLOW" | "RED"),
  "writingRatio": (0.0~1.0, 전체 글씨/필기 채움 비율),
  "traceTypes": {
    "underlineRatio": (0.0~1.0, 형광펜/밑줄 비율),
    "memoRatio": (0.0~1.0, 메모/요약 비율),
    "solutionRatio": (0.0~1.0, 풀이 과정 비율)
  },
  "partDensity": [
    {"problemNumber": 1, "problemTitle": "문제 제목", "density": (0~100)}
  ],
  "summary": "1줄 요약 (50자 이내)",
  "detailedAnalysis": "상세 분석 (최대 1000자, 한국어)",
  "mentorTip": "멘토 코칭 팁 (200자 이내, 한국어)"
}"""

SYSTEM_PROMPT = """당신은 고등학생 학습 밀도 분석 AI입니다.
학생이 제출한 학습 인증샷(공부한 노트, 문제집, 교재 사진)을 분석하여 학습 성실도를 평가합니다.

[분석 기준]
- 형광펜/밑줄 (underlineRatio): 교재나 노트에 형광펜, 밑줄, 동그라미 표시가 얼마나 있는지
- 메모/요약 (memoRatio): 여백에 메모, 요약 정리, 키워드, 부연 설명이 있는지
- 풀이 과정 (solutionRatio): 수식 전개, 단계별 풀이, 논리적 서술이 있는지
- 빈 공간: 문제지나 노트에서 비어있는 영역 비율
- 성실도: 답만 적었는지 vs 과정까지 꼼꼼히 적었는지

[신호등 기준]
- GREEN (70~100점): 형광펜+메모+풀이 과정이 풍부, 꼼꼼한 학습
- YELLOW (40~69점): 일부만 표시, 풀이 과정 부족, 보완 필요
- RED (0~39점): 거의 비어있거나, 답만 적음, 학습 흔적 부족

[중요]
- 반드시 JSON 형식으로만 응답하세요. 다른 텍스트를 포함하지 마세요.
- detailedAnalysis는 한국어로 작성하고 최대 1000자입니다.
- 이미지가 학습 자료가 아닌 경우에도 분석을 시도하되, 낮은 점수를 부여하세요."""


def _build_analysis_prompt(task, submission) -> str:
    problems_text = ""
    if task and task.problems:
        for p in task.problems:
            problems_text += f"  {p.number}번: {p.title}\n"

    comment = submission.comment or "없음"

    return f"""[과제 정보]
제목: {task.title if task else '알 수 없음'}
과목: {task.subject if task else '알 수 없음'}
문제 목록:
{problems_text if problems_text else '  문제 없음'}
멘티 코멘트: {comment}

위 과제에 대한 학습 인증샷을 분석하여 아래 JSON 형식으로 응답하세요:
{ANALYSIS_JSON_SCHEMA}"""


def _parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return json.loads(raw)


async def _call_gpt4o_vision(image_urls: list[str], prompt: str) -> dict:
    """인증샷 이미지 + 과제 정보로 GPT-4o Vision 분석"""
    client = _get_openai()

    # S3 URL → presigned URL 변환
    presigned_urls = []
    for url in image_urls[:4]:  # 최대 4장
        try:
            key = _key_from_url(url)
            presigned = generate_presigned_url(key)
            presigned_urls.append(presigned)
        except Exception:
            presigned_urls.append(url)

    content: list[dict] = [{"type": "text", "text": prompt}]
    for purl in presigned_urls:
        content.append({
            "type": "image_url",
            "image_url": {"url": purl, "detail": "high"},
        })

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        max_tokens=2000,
        temperature=0.3,
    )

    return _parse_json_response(response.choices[0].message.content or "{}")


async def _analyze_text_only(task, submission) -> dict:
    """이미지 없을 때 텍스트 데이터만으로 간이 분석"""
    client = _get_openai()

    problems_text = ""
    responses_text = ""
    if task and task.problems:
        for p in task.problems:
            problems_text += f"  {p.number}번: {p.title}\n"

    if submission.problemResponses:
        for r in submission.problemResponses:
            has_answer = "O" if r.answer else "X"
            has_note = "O" if r.textNote else "X"
            has_drawing = "O" if r.drawingUrl else "X"
            responses_text += f"  문제: 답={has_answer} 메모={has_note} 그림={has_drawing}\n"

    prompt = f"""[과제 정보]
제목: {task.title if task else '알 수 없음'}
과목: {task.subject if task else '알 수 없음'}
문제 목록:
{problems_text if problems_text else '  문제 없음'}
멘티 코멘트: {submission.comment or '없음'}
제출 텍스트: {submission.textContent or '없음'}
문제별 응답:
{responses_text if responses_text else '  응답 없음'}
자기채점: {submission.selfScoreCorrect or '?'}/{submission.selfScoreTotal or '?'}

인증샷 이미지가 없어 위 텍스트 데이터만으로 학습 밀도를 분석하세요.
아래 JSON 형식으로만 응답하세요:
{ANALYSIS_JSON_SCHEMA}"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2000,
        temperature=0.3,
    )

    return _parse_json_response(response.choices[0].message.content or "{}")


# ---------- Mock 분석 (테스트용) ----------

async def _run_mock_analysis(db: Prisma, analysis_id: str, analysis):
    await asyncio.sleep(2)

    lights = ["GREEN", "YELLOW", "RED"]
    weights = [0.5, 0.35, 0.15]
    signal = random.choices(lights, weights=weights, k=1)[0]

    score_ranges = {"GREEN": (70, 100), "YELLOW": (40, 69), "RED": (0, 39)}
    lo, hi = score_ranges[signal]
    score = random.randint(lo, hi)
    writing_ratio = round(random.uniform(20.0, 95.0), 1)

    trace_types = {
        "underlineRatio": round(random.uniform(10.0, 80.0), 1),
        "memoRatio": round(random.uniform(5.0, 50.0), 1),
        "solutionRatio": round(random.uniform(20.0, 90.0), 1),
    }

    part_density = []
    if analysis.submission and analysis.submission.task:
        problems = analysis.submission.task.problems or []
        for prob in problems:
            part_density.append({
                "problemNumber": prob.number,
                "problemTitle": prob.title[:50] if len(prob.title) > 50 else prob.title,
                "density": random.randint(max(0, score - 20), min(100, score + 20)),
            })

    mentor_tips = {
        "GREEN": "학습 밀도가 높습니다. 칭찬과 함께 다음 단계 학습을 제안해 보세요.",
        "YELLOW": "일부 보완이 필요합니다. 부족한 부분에 대해 구체적인 피드백을 주세요.",
        "RED": "학습 밀도가 낮습니다. 학습 방법에 대한 안내가 필요해 보입니다.",
    }

    await db.aianalysis.update(
        where={"id": analysis_id},
        data={
            "status": "COMPLETED",
            "signalLight": signal,
            "densityScore": score,
            "writingRatio": writing_ratio,
            "traceTypes": Json(trace_types),
            "partDensity": Json(part_density),
            "summary": f"밀도 {score}점 - {'높은 학습!' if signal == 'GREEN' else '보통' if signal == 'YELLOW' else '보완 필요'}",
            "detailedAnalysis": f"전체 학습 밀도 점수는 {score}점으로 {'매우 우수' if signal == 'GREEN' else '보통 수준' if signal == 'YELLOW' else '개선이 필요'}합니다.",
            "mentorTip": mentor_tips.get(signal, ""),
        },
    )

    if analysis.submission:
        await db.task.update(
            where={"id": analysis.submission.taskId},
            data={"status": "COMPLETED"},
        )


# ---------- 메인 분석 실행 ----------

async def run_analysis_background(db: Prisma, analysis_id: str):
    """Background task: GPT-4o Vision 또는 mock 분석 실행"""
    try:
        analysis = await db.aianalysis.find_unique(
            where={"id": analysis_id},
            include={
                "submission": {
                    "include": {
                        "task": {"include": {"problems": True}},
                        "problemResponses": True,
                    }
                }
            },
        )
        if not analysis:
            return

        # 테스트 환경이면 mock
        if _is_mock_mode():
            await _run_mock_analysis(db, analysis_id, analysis)
            return

        submission = analysis.submission
        task = submission.task if submission else None
        image_urls = submission.images if submission else []

        # GPT-4o 분석 호출
        if image_urls:
            prompt = _build_analysis_prompt(task, submission)
            result = await _call_gpt4o_vision(image_urls, prompt)
        else:
            result = await _analyze_text_only(task, submission)

        # partDensity 보강 (GPT가 비워두면 문제 목록으로 채움)
        part_density = result.get("partDensity", [])
        if not part_density and task and task.problems:
            base_score = result.get("densityScore", 50)
            for prob in task.problems:
                part_density.append({
                    "problemNumber": prob.number,
                    "problemTitle": prob.title[:50],
                    "density": base_score,
                })

        trace_types = result.get("traceTypes", {
            "underlineRatio": 0.0,
            "memoRatio": 0.0,
            "solutionRatio": 0.0,
        })

        await db.aianalysis.update(
            where={"id": analysis_id},
            data={
                "status": "COMPLETED",
                "signalLight": result.get("signalLight", "YELLOW"),
                "densityScore": result.get("densityScore", 50),
                "writingRatio": result.get("writingRatio", 0.5),
                "traceTypes": Json(trace_types),
                "partDensity": Json(part_density),
                "summary": result.get("summary", "")[:200],
                "detailedAnalysis": result.get("detailedAnalysis", "")[:1000],
                "mentorTip": result.get("mentorTip", "")[:500],
            },
        )

        if submission:
            await db.task.update(
                where={"id": submission.taskId},
                data={"status": "COMPLETED"},
            )

    except Exception as e:
        logger.error(f"Analysis failed for {analysis_id}: {e}")
        try:
            await db.aianalysis.update(
                where={"id": analysis_id},
                data={"status": "FAILED"},
            )
        except Exception:
            pass
