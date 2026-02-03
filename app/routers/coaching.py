from fastapi import APIRouter, Depends
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.coaching import (
    AssignMaterialRequest,
    AiDraftResponse,
    CoachingDetailResponse,
    RecommendationsResponse,
)
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.task import TaskResponse
from app.services import coaching_service

router = APIRouter(prefix="/api/coaching", tags=["Coaching Center"])


@router.get(
    "/{submissionId}",
    response_model=SuccessResponse[CoachingDetailResponse],
    summary="코칭 종합 조회",
    description="인증샷, AI 분석 결과, 과제 정보를 종합 조회합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "멘토 권한 필요"},
        404: {"model": ErrorResponse, "description": "제출 내역 없음"},
    },
)
async def get_coaching_detail(
    submissionId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await coaching_service.get_coaching_detail(db, current_user, submissionId)
    return SuccessResponse(data=result)


@router.get(
    "/{submissionId}/ai-draft",
    response_model=SuccessResponse[AiDraftResponse],
    summary="AI 피드백 초안",
    description="AI가 생성한 피드백 초안을 조회합니다. 분석 완료 후 사용 가능합니다.",
    responses={
        400: {"model": ErrorResponse, "description": "분석 미완료 (ANALYSIS_001)"},
        404: {"model": ErrorResponse, "description": "제출 내역 없음"},
    },
)
async def get_ai_draft(
    submissionId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await coaching_service.get_ai_draft(db, current_user, submissionId)
    return SuccessResponse(data=AiDraftResponse(**result))


@router.get(
    "/{submissionId}/recommendations",
    response_model=SuccessResponse[RecommendationsResponse],
    summary="보완 학습지 추천",
    description="제출물의 과목/능력태그 기반으로 보완 학습지를 추천합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "멘토 권한 필요"},
        404: {"model": ErrorResponse, "description": "제출 내역 없음"},
    },
)
async def get_recommendations(
    submissionId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await coaching_service.get_recommendations(db, current_user, submissionId)
    return SuccessResponse(data=RecommendationsResponse(**result))


@router.post(
    "/assign-material",
    response_model=SuccessResponse[TaskResponse],
    status_code=201,
    summary="학습지 배정",
    description="보완 학습지를 멘티 할 일로 추가합니다. isLocked=true로 생성됩니다.",
    responses={
        403: {"model": ErrorResponse, "description": "멘토 권한 필요 / 담당 멘티만 가능"},
        404: {"model": ErrorResponse, "description": "학습지 없음"},
    },
)
async def assign_material(
    data: AssignMaterialRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    task = await coaching_service.assign_material(db, current_user, data)
    return SuccessResponse(data=TaskResponse.model_validate(task))
