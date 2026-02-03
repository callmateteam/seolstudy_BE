from fastapi import APIRouter, Depends
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.parent import (
    MenteeStatusResponse,
    MentorInfoResponse,
    ParentDashboardResponse,
)
from app.services import parent_service

router = APIRouter(prefix="/api/parent", tags=["Parent"])


@router.get(
    "/dashboard",
    response_model=SuccessResponse[ParentDashboardResponse],
    summary="학부모 대시보드",
    description="자녀의 오늘 학습 현황, 담당 멘토 정보, 최근 피드백 횟수를 종합 조회합니다.",
    responses={403: {"model": ErrorResponse, "description": "학부모 권한 필요"}},
)
async def get_dashboard(
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await parent_service.get_dashboard(db, current_user)
    return SuccessResponse(data=ParentDashboardResponse(**result))


@router.get(
    "/mentee-status",
    response_model=SuccessResponse[MenteeStatusResponse],
    summary="자녀 학습 현황",
    description="이번 주 일별 완수율과 주간 총 할 일/완료 수를 조회합니다.",
    responses={403: {"model": ErrorResponse, "description": "학부모 권한 필요"}},
)
async def get_mentee_status(
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await parent_service.get_mentee_status(db, current_user)
    return SuccessResponse(data=MenteeStatusResponse(**result))


@router.get(
    "/mentor-info",
    response_model=SuccessResponse[MentorInfoResponse],
    summary="담당 멘토 정보",
    description="자녀의 담당 멘토 정보와 최근 7일간 피드백 횟수를 조회합니다.",
    responses={403: {"model": ErrorResponse, "description": "학부모 권한 필요"}},
)
async def get_mentor_info(
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await parent_service.get_mentor_info(db, current_user)
    return SuccessResponse(data=MentorInfoResponse(**result))
