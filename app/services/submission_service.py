from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.submission import SelfScoreRequest, SubmissionCreateRequest


async def create_submission(
    db: Prisma, user, task_id: str, data: SubmissionCreateRequest
):
    if not user.menteeProfile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_001", "message": "온보딩을 먼저 완료해주세요"},
        )

    task = await db.task.find_unique(where={"id": task_id})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_002", "message": "할 일을 찾을 수 없습니다"},
        )

    if task.menteeId != user.menteeProfile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "본인의 데이터만 접근 가능합니다"},
        )

    if data.submissionType == "TEXT" and not data.textContent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_002", "message": "TEXT 모드에서는 textContent가 필요합니다"},
        )

    if data.submissionType == "DRAWING" and (not data.images or len(data.images) == 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_002", "message": "DRAWING 모드에서는 이미지가 필요합니다"},
        )

    submission = await db.tasksubmission.create(
        data={
            "task": {"connect": {"id": task_id}},
            "mentee": {"connect": {"id": user.menteeProfile.id}},
            "submissionType": data.submissionType,
            "textContent": data.textContent if data.submissionType == "TEXT" else None,
            "images": data.images if data.submissionType == "DRAWING" else [],
        }
    )

    await db.task.update(
        where={"id": task_id},
        data={"status": "SUBMITTED"},
    )

    return submission


async def get_submissions(db: Prisma, task_id: str):
    task = await db.task.find_unique(where={"id": task_id})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_002", "message": "할 일을 찾을 수 없습니다"},
        )

    return await db.tasksubmission.find_many(
        where={"taskId": task_id},
        order={"submittedAt": "desc"},
    )


async def update_self_score(
    db: Prisma, user, submission_id: str, data: SelfScoreRequest
):
    submission = await db.tasksubmission.find_unique(where={"id": submission_id})
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUBMIT_003", "message": "제출 내역을 찾을 수 없습니다"},
        )

    if not user.menteeProfile or submission.menteeId != user.menteeProfile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "본인의 데이터만 접근 가능합니다"},
        )

    if data.selfScoreCorrect > data.selfScoreTotal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_004", "message": "맞은 문제 수가 전체 문제 수보다 클 수 없습니다"},
        )

    updated = await db.tasksubmission.update(
        where={"id": submission_id},
        data={
            "selfScoreCorrect": data.selfScoreCorrect,
            "selfScoreTotal": data.selfScoreTotal,
            "wrongQuestions": data.wrongQuestions,
        },
    )
    return updated
