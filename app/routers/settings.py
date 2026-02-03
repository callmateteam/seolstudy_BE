from fastapi import APIRouter, Depends
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.settings import (
    MenteeSettingsRequest,
    MentorSettingsRequest,
    ProfileResponse,
    ProfileUpdateRequest,
)
from app.services import settings_service

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get(
    "/profile",
    response_model=SuccessResponse[ProfileResponse],
    summary="프로필 조회",
    description="현재 로그인한 사용자의 프로필 정보를 조회합니다.",
)
async def get_profile(
    current_user=Depends(get_current_user),
):
    result = await settings_service.get_profile(current_user)
    return SuccessResponse(data=ProfileResponse(**result))


@router.put(
    "/profile",
    response_model=SuccessResponse[ProfileResponse],
    summary="프로필 수정",
    description="이름, 전화번호, 닉네임, 프로필 이미지를 수정합니다.",
    responses={
        400: {"model": ErrorResponse, "description": "수정할 내용 없음"},
    },
)
async def update_profile(
    data: ProfileUpdateRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await settings_service.update_profile(db, current_user, data)
    return SuccessResponse(data=ProfileResponse(**result))


@router.put(
    "/mentee",
    response_model=SuccessResponse[dict],
    summary="멘티 설정 수정",
    description="목표 등급, 과목 등 멘티 학습 설정을 수정합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "멘티 권한 필요"},
    },
)
async def update_mentee_settings(
    data: MenteeSettingsRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await settings_service.update_mentee_settings(db, current_user, data)
    return SuccessResponse(data=result)


@router.put(
    "/mentor",
    response_model=SuccessResponse[dict],
    summary="멘토 설정 수정",
    description="담당 과목 등 멘토 설정을 수정합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "멘토 권한 필요"},
    },
)
async def update_mentor_settings(
    data: MentorSettingsRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await settings_service.update_mentor_settings(db, current_user, data)
    return SuccessResponse(data=result)
