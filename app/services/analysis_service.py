import asyncio
import random

from fastapi import HTTPException, status
from prisma import Prisma


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


async def run_analysis_background(db: Prisma, analysis_id: str):
    """Background task that simulates AI analysis."""
    await asyncio.sleep(2)

    try:
        lights = ["GREEN", "YELLOW", "RED"]
        weights = [0.5, 0.35, 0.15]
        signal = random.choices(lights, weights=weights, k=1)[0]

        score_ranges = {"GREEN": (70, 100), "YELLOW": (40, 69), "RED": (0, 39)}
        lo, hi = score_ranges[signal]
        score = random.randint(lo, hi)
        writing_ratio = round(random.uniform(20.0, 95.0), 1)

        analysis = await db.aianalysis.update(
            where={"id": analysis_id},
            data={
                "status": "COMPLETED",
                "signalLight": signal,
                "densityScore": score,
                "writingRatio": writing_ratio,
                "summary": f"학습 밀도 분석 완료. 신호등: {signal}, 점수: {score}점",
            },
            include={"submission": True},
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
