import datetime as dt

from fastapi import APIRouter, Depends
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.feedback import FeedbackBySubjectItem, FeedbackDetailResponse
from app.services import feedback_service

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


@router.get(
    "",
    response_model=SuccessResponse[list[FeedbackDetailResponse]],
    summary="날짜별 피드백 조회",
    description="특정 날짜의 피드백 목록을 조회합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "권한 없음"},
    },
)
async def get_feedback_by_date(
    menteeId: str,
    date: dt.date,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    results = await feedback_service.get_feedback_by_date(db, menteeId, date)
    return SuccessResponse(data=[FeedbackDetailResponse(**r) for r in results])


@router.get(
    "/by-subject",
    response_model=SuccessResponse[list[FeedbackBySubjectItem]],
    summary="과목별 피드백 조회",
    description="특정 과목의 피드백을 최신순으로 조회합니다. 과제별 멘토 피드백, AI 분석 요약, 학습 밀도를 포함합니다.",
)
async def get_feedback_by_subject(
    menteeId: str,
    subject: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    results = await feedback_service.get_feedback_by_subject(db, menteeId, subject)
    return SuccessResponse(data=[FeedbackBySubjectItem(**r) for r in results])


@router.get(
    "/{feedbackId}",
    response_model=SuccessResponse[FeedbackDetailResponse],
    summary="피드백 상세 조회",
    description="피드백의 상세 내용(할 일별 피드백 + 총평)을 조회합니다.",
    responses={
        404: {"model": ErrorResponse, "description": "피드백 없음 (FEEDBACK_002)"},
    },
)
async def get_feedback_detail(
    feedbackId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await feedback_service.get_feedback_detail(db, feedbackId)
    return SuccessResponse(data=FeedbackDetailResponse(**result))
