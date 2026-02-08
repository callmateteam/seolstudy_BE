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


# ---------- 학습 밀도 공식 ----------
# A. 과제점수 (50%): (정답 수 / 전체 문제 수) * 100
# B. 필기점수 (20%): min(100, (필기율 / 20) * 100) — 필기율 20% 이상이면 만점
# C. 시간점수 (30%): 목표 이상이면 100, 미만이면 (실제 / 목표) * 100
# 신호등: 70↑ GREEN, 40↑ YELLOW, 미만 RED

WEIGHT_TASK = 0.5
WEIGHT_WRITING = 0.2
WEIGHT_TIME = 0.3


def _calc_task_score(submission) -> float:
    """A. 과제점수: (정답 수 / 전체 문제 수) * 100"""
    correct = submission.selfScoreCorrect
    total = submission.selfScoreTotal
    if not total or total <= 0:
        return 100.0  # 문제 없는 과제는 만점 처리
    if correct is None:
        return 0.0
    return min(100.0, (correct / total) * 100)


def _calc_writing_score(writing_ratio_pct: float) -> float:
    """B. 필기점수: min(100, (필기율% / 20) * 100) — 20% 이상이면 만점"""
    return min(100.0, (writing_ratio_pct / 20.0) * 100)


def _calc_time_score(task) -> float:
    """C. 시간점수: 목표시간 대비 실제 공부 시간"""
    target = task.targetStudyMinutes if task else None
    actual = task.studyTimeMinutes if task else None
    if not target or target <= 0:
        return 100.0  # 목표시간 미설정이면 만점 처리
    if not actual or actual <= 0:
        return 0.0
    if actual >= target:
        return 100.0
    return (actual / target) * 100


def _calc_density(task_score: float, writing_score: float, time_score: float) -> int:
    """최종 밀도 점수 = A*0.5 + B*0.2 + C*0.3"""
    raw = task_score * WEIGHT_TASK + writing_score * WEIGHT_WRITING + time_score * WEIGHT_TIME
    return max(0, min(100, round(raw)))


def _signal_light(score: int) -> str:
    if score >= 70:
        return "GREEN"
    if score >= 40:
        return "YELLOW"
    return "RED"


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


# ---------- GPT-4o Vision (필기율 + 정성 분석) ----------

VISION_JSON_SCHEMA = """{
  "writingRatio": (0~100 정수, 필기가 차지하는 면적 비율 %),
  "traceTypes": {
    "underlineRatio": (0~100, 형광펜/밑줄/동그라미 면적 비율 %),
    "memoRatio": (0~100, 손글씨 메모/요약/정리 면적 비율 %),
    "solutionRatio": (0~100, 수식풀이/논리서술 면적 비율 %)
  },
  "partDensity": [
    {"problemNumber": 1, "problemTitle": "문제 제목", "density": (0~100)}
  ],
  "summary": "구체적 학습 내용 1줄 요약 (50자 이내, 예: '미적분 극값 문제 3문항 풀이, 풀이 과정 상세')",
  "detailedAnalysis": "상세 분석 (최대 1000자, 한국어)",
  "mentorTip": "멘토 코칭 팁 (200자 이내, 한국어)"
}"""

SYSTEM_PROMPT = """당신은 고등학생 학습 인증샷 분석 AI입니다.
학생이 제출한 학습 인증샷(노트, 문제집, 교재 사진)에서 학습 흔적을 정량 분석합니다.

[핵심: writingRatio 측정법]
전체 페이지 면적 대비 "학생이 직접 남긴 흔적"의 면적 비율(%)을 산출합니다.
다음은 모두 필기(학습 흔적)에 포함합니다:
  ✓ 손글씨 (메모, 요약, 정리 노트, 단어 뜻 기재)
  ✓ 형광펜 하이라이팅 (색상 불문, 형광펜으로 칠한 영역 전체)
  ✓ 밑줄, 동그라미, 체크 표시, 별표, 화살표
  ✓ 수식 풀이, 계산 과정, 그래프 그리기
  ✓ 오답 표시(X, △), 정답 체크(O, ✓)
다음은 필기에 포함하지 않습니다:
  ✗ 인쇄된 텍스트 (문제지, 교재 원문)
  ✗ 인쇄된 그림, 표, 선

[traceTypes 규칙]
underlineRatio + memoRatio + solutionRatio ≈ writingRatio 이어야 합니다.
각 항목은 겹치지 않게 분류하세요:
  - underlineRatio: 형광펜 하이라이팅, 밑줄, 동그라미, 체크/별표 (표시류)
  - memoRatio: 손글씨 메모, 요약 정리, 단어 뜻, 키워드 정리 (서술류)
  - solutionRatio: 수식 전개, 계산 과정, 단계별 풀이 (풀이류)

[과목별 특성 참고]
- 국어: 메모/요약(memoRatio)이 높은 경향. 문법 정리 노트는 writingRatio 80~100%
- 영어: 형광펜 하이라이팅(underlineRatio)이 높은 경향. 교재에 형광펜+여백 메모가 있으면 writingRatio 40~70%
- 수학: 풀이 과정(solutionRatio)이 높은 경향. 풀이 있는 문제지는 writingRatio 50~70%

[참고 기준 예시]
예시1) 영어 교재에 형광펜+밑줄+여백 메모 → writingRatio=50, underline=30, memo=15, solution=5
예시2) 수학 문제지에 풀이 과정+메모 → writingRatio=60, underline=5, memo=10, solution=45
예시3) 국어 문법 손글씨 노트 → writingRatio=90, underline=0, memo=85, solution=5

[summary 작성 규칙]
- "~포함되어 있음", "~이미지입니다" 같은 일반적 표현 금지
- 구체적인 학습 단원/내용 + 필기 특징을 포함하세요
- 좋은 예: "확률밀도함수 적분 풀이 3문항, 계산 과정 상세"
- 나쁜 예: "수학 문제 풀이와 메모가 포함되어 있음"

[중요]
- 반드시 JSON 형식으로만 응답하세요. 다른 텍스트를 포함하지 마세요.
- writingRatio는 0~100 사이 정수 (%)로 응답하세요.
- detailedAnalysis는 한국어로 작성하고 최대 1000자입니다.
- 형광펜이 많은 이미지를 writingRatio 30% 이하로 과소평가하지 마세요."""


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
{VISION_JSON_SCHEMA}"""


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

    presigned_urls = []
    for url in image_urls[:4]:
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

인증샷 이미지가 없어 위 텍스트 데이터만으로 분석하세요.
아래 JSON 형식으로만 응답하세요:
{VISION_JSON_SCHEMA}"""

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

    submission = analysis.submission
    task = submission.task if submission else None

    # mock 필기율
    writing_ratio = round(random.uniform(10.0, 60.0), 1)

    # 공식 기반 점수 계산
    task_score = _calc_task_score(submission) if submission else 50.0
    writing_score = _calc_writing_score(writing_ratio)
    time_score = _calc_time_score(task) if task else 50.0
    score = _calc_density(task_score, writing_score, time_score)
    signal = _signal_light(score)

    trace_types = {
        "underlineRatio": round(random.uniform(10.0, 80.0), 1),
        "memoRatio": round(random.uniform(5.0, 50.0), 1),
        "solutionRatio": round(random.uniform(20.0, 90.0), 1),
    }

    part_density = []
    if task and task.problems:
        for prob in task.problems:
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

    detail = (
        f"과제점수 {task_score:.0f}점(50%), "
        f"필기점수 {writing_score:.0f}점(20%), "
        f"시간점수 {time_score:.0f}점(30%) → "
        f"종합 {score}점"
    )

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
            "detailedAnalysis": detail,
            "mentorTip": mentor_tips.get(signal, ""),
        },
    )

    if submission:
        await db.task.update(
            where={"id": submission.taskId},
            data={"status": "COMPLETED"},
        )


# ---------- 메인 분석 실행 ----------

async def run_analysis_background(db: Prisma, analysis_id: str):
    """Background task: 공식 기반 밀도 점수 + GPT-4o 필기율 분석"""
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

        if _is_mock_mode():
            await _run_mock_analysis(db, analysis_id, analysis)
            return

        submission = analysis.submission
        task = submission.task if submission else None
        image_urls = submission.images if submission else []

        # 1) GPT-4o로 필기율 + 정성 분석
        if image_urls:
            prompt = _build_analysis_prompt(task, submission)
            gpt_result = await _call_gpt4o_vision(image_urls, prompt)
        else:
            gpt_result = await _analyze_text_only(task, submission)

        # 2) GPT 결과에서 필기율 추출 (0~100%)
        writing_ratio = float(gpt_result.get("writingRatio", 0))
        if writing_ratio > 100:
            writing_ratio = 100.0

        # 3) 공식 기반 밀도 점수 계산
        task_score = _calc_task_score(submission) if submission else 0.0
        writing_score = _calc_writing_score(writing_ratio)
        time_score = _calc_time_score(task) if task else 0.0
        density_score = _calc_density(task_score, writing_score, time_score)
        signal = _signal_light(density_score)

        # 4) partDensity 보강
        part_density = gpt_result.get("partDensity", [])
        if not part_density and task and task.problems:
            for prob in task.problems:
                part_density.append({
                    "problemNumber": prob.number,
                    "problemTitle": prob.title[:50],
                    "density": density_score,
                })

        trace_types = gpt_result.get("traceTypes", {
            "underlineRatio": 0.0,
            "memoRatio": 0.0,
            "solutionRatio": 0.0,
        })

        detail_prefix = (
            f"[점수 산출] 과제 {task_score:.0f}×0.5={task_score*WEIGHT_TASK:.0f}, "
            f"필기 {writing_score:.0f}×0.2={writing_score*WEIGHT_WRITING:.0f}, "
            f"시간 {time_score:.0f}×0.3={time_score*WEIGHT_TIME:.0f} → 총 {density_score}점\n\n"
        )
        gpt_detail = gpt_result.get("detailedAnalysis", "")
        full_detail = (detail_prefix + gpt_detail)[:1000]

        await db.aianalysis.update(
            where={"id": analysis_id},
            data={
                "status": "COMPLETED",
                "signalLight": signal,
                "densityScore": density_score,
                "writingRatio": writing_ratio,
                "traceTypes": Json(trace_types),
                "partDensity": Json(part_density),
                "summary": gpt_result.get("summary", "")[:200],
                "detailedAnalysis": full_detail,
                "mentorTip": gpt_result.get("mentorTip", "")[:500],
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
