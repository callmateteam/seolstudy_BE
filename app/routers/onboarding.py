from fastapi import APIRouter, Depends, status
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.onboarding import (
    MenteeOnboardingRequest,
    MenteeProfileResponse,
    MentorOnboardingRequest,
    MentorProfileResponse,
    ParentOnboardingRequest,
    ParentProfileResponse,
)
from app.services import onboarding_service

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


@router.put(
    "/mentee",
    response_model=SuccessResponse[MenteeProfileResponse],
    summary="멘티 온보딩",
    description="멘티 프로필을 생성합니다. 학년, 수강 과목, 현재/목표 등급을 입력합니다. 완료 후 초대 코드가 자동 생성됩니다.",
    responses={
        403: {"model": ErrorResponse, "description": "멘티 권한 없음 (PERM_001)"},
        409: {"model": ErrorResponse, "description": "이미 온보딩 완료 (ONBOARD_003)"},
    },
)
async def onboard_mentee(
    data: MenteeOnboardingRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    profile = await onboarding_service.onboard_mentee(db, current_user, data)
    return SuccessResponse(data=MenteeProfileResponse.model_validate(profile))


@router.put(
    "/mentor",
    response_model=SuccessResponse[MentorProfileResponse],
    summary="멘토 온보딩",
    description="멘토 프로필을 생성합니다. 대학, 학과, 코칭 가능 과목, 코칭 경험 여부를 입력합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "멘토 권한 없음 (PERM_001)"},
        409: {"model": ErrorResponse, "description": "이미 온보딩 완료 (ONBOARD_003)"},
    },
)
async def onboard_mentor(
    data: MentorOnboardingRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    profile = await onboarding_service.onboard_mentor(db, current_user, data)
    return SuccessResponse(data=MentorProfileResponse.model_validate(profile))


@router.put(
    "/parent",
    response_model=SuccessResponse[ParentProfileResponse],
    summary="학부모 온보딩",
    description="학부모 프로필을 생성합니다. 멘티(자녀)의 초대 코드를 입력하여 자녀와 연결합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "학부모 권한 없음 (PERM_001)"},
        404: {"model": ErrorResponse, "description": "유효하지 않은 초대 코드 (ONBOARD_004)"},
        409: {"model": ErrorResponse, "description": "이미 온보딩 완료 (ONBOARD_003)"},
    },
)
async def onboard_parent(
    data: ParentOnboardingRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    profile = await onboarding_service.onboard_parent(db, current_user, data)
    return SuccessResponse(data=ParentProfileResponse.model_validate(profile))
