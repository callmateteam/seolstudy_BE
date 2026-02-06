import asyncio
import random

from fastapi import HTTPException, status
from prisma import Json, Prisma


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


def _generate_detailed_analysis(signal: str, score: int, trace_types: dict) -> str:
    """상세 분석 텍스트 생성 (최대 1000자)"""
    underline = trace_types.get("underlineRatio", 0)
    memo = trace_types.get("memoRatio", 0)
    solution = trace_types.get("solutionRatio", 0)

    if signal == "GREEN":
        return (
            f"전체 학습 밀도 점수는 {score}점으로 매우 우수합니다. "
            f"형광펜/밑줄 비율이 {underline:.1f}%로 핵심 내용을 잘 파악하고 있으며, "
            f"메모/요약 비율 {memo:.1f}%, 풀이 과정 비율 {solution:.1f}%로 "
            "전반적으로 꼼꼼하게 학습한 흔적이 보입니다. "
            "특히 풀이 과정을 상세히 기록하여 이해도가 높아 보입니다. "
            "이 조자로 계속 학습을 이어가면 좋겠습니다. "
            "다음 학습에서도 동일한 방식으로 진행해 주세요."
        )
    elif signal == "YELLOW":
        return (
            f"전체 학습 밀도 점수는 {score}점으로 보통 수준입니다. "
            f"형광펜/밑줄 비율이 {underline:.1f}%로 일부 핵심 내용을 표시했지만, "
            f"메모/요약 비율 {memo:.1f}%, 풀이 과정 비율 {solution:.1f}%로 "
            "보충이 필요한 부분이 있습니다. "
            "특히 풀이 과정을 더 상세히 기록하면 이해도 향상에 도움이 됩니다. "
            "다음 학습에서는 중요 개념을 메모하고 풀이 과정을 빠짐없이 적어보세요."
        )
    else:
        return (
            f"전체 학습 밀도 점수는 {score}점으로 개선이 필요합니다. "
            f"형광펜/밑줄 비율이 {underline:.1f}%로 핵심 내용 파악이 부족하며, "
            f"메모/요약 비율 {memo:.1f}%, 풀이 과정 비율 {solution:.1f}%로 "
            "학습 흔적이 충분하지 않습니다. "
            "문제를 풀 때는 반드시 풀이 과정을 적고, 중요 부분에 형광펜 표시를 해주세요. "
            "이해가 어려운 부분은 메모를 남겨 멘토와 함께 점검하면 좋겠습니다. "
            "다음 학습에서는 더 꼼꼼히 학습해 주세요."
        )


async def run_analysis_background(db: Prisma, analysis_id: str):
    """Background task that simulates AI analysis."""
    await asyncio.sleep(2)

    try:
        # 분석 및 관련 데이터 조회
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

        lights = ["GREEN", "YELLOW", "RED"]
        weights = [0.5, 0.35, 0.15]
        signal = random.choices(lights, weights=weights, k=1)[0]

        score_ranges = {"GREEN": (70, 100), "YELLOW": (40, 69), "RED": (0, 39)}
        lo, hi = score_ranges[signal]
        score = random.randint(lo, hi)
        writing_ratio = round(random.uniform(20.0, 95.0), 1)

        # 풀이 흔적 유형별 비율 (mock)
        trace_types = {
            "underlineRatio": round(random.uniform(10.0, 80.0), 1),
            "memoRatio": round(random.uniform(5.0, 50.0), 1),
            "solutionRatio": round(random.uniform(20.0, 90.0), 1),
        }

        # 문제별 밀도 분석 (mock)
        part_density = []
        if analysis.submission and analysis.submission.task:
            problems = analysis.submission.task.problems or []
            for prob in problems:
                part_density.append({
                    "problemNumber": prob.number,
                    "problemTitle": prob.title[:50] if len(prob.title) > 50 else prob.title,
                    "density": random.randint(max(0, score - 20), min(100, score + 20)),
                })

        # 상세 분석 텍스트 생성
        detailed_analysis = _generate_detailed_analysis(signal, score, trace_types)

        # 멘토 팁 생성
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
                "detailedAnalysis": detailed_analysis,
                "mentorTip": mentor_tips.get(signal, ""),
            },
        )

        if analysis.submission:
            await db.task.update(
                where={"id": analysis.submission.taskId},
                data={"status": "COMPLETED"},
            )
    except Exception:
        await db.aianalysis.update(
            where={"id": analysis_id},
            data={"status": "FAILED"},
        )


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
