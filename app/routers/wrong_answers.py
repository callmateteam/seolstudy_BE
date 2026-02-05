from fastapi import APIRouter, Depends, Query
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.analysis import WrongAnswerSheetCompleteRequest, WrongAnswerSheetResponse
from app.schemas.common import ErrorResponse, SuccessResponse
from app.services import wrong_answer_service

router = APIRouter(prefix="/api/wrong-answers", tags=["Wrong Answers"])


@router.get(
    "",
    response_model=SuccessResponse[list[WrongAnswerSheetResponse]],
    summary="오답 학습지 목록 조회",
    description="멘티의 오답 학습지 목록을 조회합니다. submissionId로 필터링 가능.",
    responses={
        401: {"model": ErrorResponse, "description": "인증 실패"},
    },
)
async def get_wrong_answer_sheets(
    submissionId: str | None = Query(default=None, description="제출물 ID로 필터링"),
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    if not current_user.menteeProfile:
        return SuccessResponse(data=[])

    sheets = await wrong_answer_service.get_wrong_answer_sheets(
        db, current_user.menteeProfile.id, submissionId
    )
    return SuccessResponse(data=[WrongAnswerSheetResponse.model_validate(s) for s in sheets])


@router.get(
    "/{sheetId}",
    response_model=SuccessResponse[WrongAnswerSheetResponse],
    summary="오답 학습지 상세 조회",
    description="특정 오답 학습지의 상세 정보를 조회합니다.",
    responses={
        404: {"model": ErrorResponse, "description": "오답 학습지 없음 (WRONG_001)"},
    },
)
async def get_wrong_answer_sheet(
    sheetId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    sheet = await wrong_answer_service.get_wrong_answer_sheet(db, sheetId)
    return SuccessResponse(data=WrongAnswerSheetResponse.model_validate(sheet))


@router.patch(
    "/{sheetId}/complete",
    response_model=SuccessResponse[WrongAnswerSheetResponse],
    summary="오답 학습지 완료 처리",
    description="오답 학습지를 완료 또는 미완료 상태로 변경합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "본인 데이터만 접근 가능 (PERM_002)"},
        404: {"model": ErrorResponse, "description": "오답 학습지 없음 (WRONG_001)"},
    },
)
async def complete_wrong_answer_sheet(
    sheetId: str,
    data: WrongAnswerSheetCompleteRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    sheet = await wrong_answer_service.complete_wrong_answer_sheet(
        db, current_user, sheetId, data.isCompleted
    )
    return SuccessResponse(data=WrongAnswerSheetResponse.model_validate(sheet))
