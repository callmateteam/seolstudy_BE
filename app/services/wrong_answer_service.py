from fastapi import HTTPException, status
from prisma import Prisma


async def get_wrong_answer_sheets(db: Prisma, mentee_id: str, submission_id: str | None = None):
    """오답 학습지 목록 조회"""
    where: dict = {"menteeId": mentee_id}
    if submission_id:
        where["submissionId"] = submission_id

    sheets = await db.wronganswersheet.find_many(
        where=where,
        order={"createdAt": "desc"},
    )
    return sheets


async def get_wrong_answer_sheet(db: Prisma, sheet_id: str):
    """오답 학습지 상세 조회"""
    sheet = await db.wronganswersheet.find_unique(where={"id": sheet_id})
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WRONG_001", "message": "오답 학습지를 찾을 수 없습니다"},
        )
    return sheet


async def complete_wrong_answer_sheet(db: Prisma, user, sheet_id: str, is_completed: bool):
    """오답 학습지 완료 처리"""
    sheet = await db.wronganswersheet.find_unique(where={"id": sheet_id})
    if not sheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WRONG_001", "message": "오답 학습지를 찾을 수 없습니다"},
        )

    if not user.menteeProfile or sheet.menteeId != user.menteeProfile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "본인의 데이터만 접근 가능합니다"},
        )

    from datetime import datetime

    update_data: dict = {"isCompleted": is_completed}
    if is_completed:
        update_data["completedAt"] = datetime.utcnow()
    else:
        update_data["completedAt"] = None

    updated = await db.wronganswersheet.update(
        where={"id": sheet_id},
        data=update_data,
    )
    return updated


async def create_wrong_answer_sheets_for_submission(
    db: Prisma, submission_id: str, mentee_id: str, wrong_problems: list[dict]
):
    """제출물의 틀린 문제에 대한 오답 학습지 생성"""
    for wp in wrong_problems:
        await db.wronganswersheet.create(
            data={
                "submissionId": submission_id,
                "menteeId": mentee_id,
                "problemId": wp["problemId"],
                "problemNumber": wp["problemNumber"],
                "problemTitle": wp["problemTitle"],
                "originalAnswer": wp.get("originalAnswer"),
                "correctAnswer": wp.get("correctAnswer"),
                "explanation": wp.get("explanation"),
                "relatedConcepts": wp.get("relatedConcepts", []),
            }
        )
