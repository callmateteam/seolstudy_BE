from fastapi import APIRouter, Depends
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.mentor import (
    DashboardResponse,
    FeedbackCreateRequest,
    FeedbackResponse,
    JudgmentModifyRequest,
    JudgmentResponse,
    MenteeDetailResponse,
    MenteeListItem,
    ReviewQueueItem,
)
from app.schemas.task import TaskResponse
from app.services import mentor_service

router = APIRouter(prefix="/api/mentor", tags=["Mentor"])


@router.get(
    "/dashboard",
    response_model=SuccessResponse[DashboardResponse],
    summary="멘토 대시보드",
    description="담당 멘티 목록과 검토 대기열을 종합 조회합니다.",
    responses={403: {"model": ErrorResponse, "description": "멘토 권한 필요"}},
)
async def get_dashboard(
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await mentor_service.get_dashboard(db, current_user)
    return SuccessResponse(data=DashboardResponse(**result))


@router.get(
    "/mentees",
    response_model=SuccessResponse[list[MenteeListItem]],
    summary="담당 멘티 목록",
    description="멘토에게 배정된 멘티 목록과 오늘의 할 일 현황을 조회합니다.",
    responses={403: {"model": ErrorResponse, "description": "멘토 권한 필요"}},
)
async def get_mentees(
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await mentor_service.get_mentee_list(db, current_user)
    return SuccessResponse(data=[MenteeListItem(**m) for m in result])


@router.get(
    "/mentees/{menteeId}",
    response_model=SuccessResponse[MenteeDetailResponse],
    summary="멘티 상세 조회",
    description="담당 멘티의 오늘 플래너, 과제 현황, 완수율을 조회합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "담당 멘티만 접근 가능"},
        404: {"model": ErrorResponse, "description": "멘티 없음"},
    },
)
async def get_mentee_detail(
    menteeId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await mentor_service.get_mentee_detail(db, current_user, menteeId)
    return SuccessResponse(
        data=MenteeDetailResponse(
            menteeId=result["menteeId"],
            name=result["name"],
            grade=result["grade"],
            subjects=result["subjects"],
            tasks=[TaskResponse.model_validate(t) for t in result["tasks"]],
            completionRate=result["completionRate"],
        )
    )


@router.get(
    "/review-queue",
    response_model=SuccessResponse[list[ReviewQueueItem]],
    summary="검토 대기열",
    description="판정 미완료인 제출 목록을 RED 우선, 경과시간 순으로 정렬합니다.",
    responses={403: {"model": ErrorResponse, "description": "멘토 권한 필요"}},
)
async def get_review_queue(
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await mentor_service.get_review_queue(db, current_user)
    return SuccessResponse(data=[ReviewQueueItem(**r) for r in result])


# === Judgment ===

@router.post(
    "/judgments/{analysisId}/confirm",
    response_model=SuccessResponse[JudgmentResponse],
    status_code=201,
    summary="AI 판정 확정",
    description="AI 분석 결과를 그대로 확정합니다.",
    responses={
        404: {"model": ErrorResponse, "description": "분석 결과 없음 (JUDGE_001)"},
        409: {"model": ErrorResponse, "description": "이미 판정 완료 (JUDGE_002)"},
    },
)
async def confirm_judgment(
    analysisId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    judgment = await mentor_service.confirm_judgment(db, current_user, analysisId)
    return SuccessResponse(data=JudgmentResponse.model_validate(judgment))


@router.post(
    "/judgments/{analysisId}/modify",
    response_model=SuccessResponse[JudgmentResponse],
    status_code=201,
    summary="판정 수정",
    description="AI 분석 결과를 수정합니다. reason(사유)은 필수입니다.",
    responses={
        404: {"model": ErrorResponse, "description": "분석 결과 없음 (JUDGE_001)"},
        409: {"model": ErrorResponse, "description": "이미 판정 완료 (JUDGE_002)"},
    },
)
async def modify_judgment(
    analysisId: str,
    data: JudgmentModifyRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    judgment = await mentor_service.modify_judgment(db, current_user, analysisId, data)
    return SuccessResponse(data=JudgmentResponse.model_validate(judgment))


@router.get(
    "/judgments/{analysisId}",
    response_model=SuccessResponse[JudgmentResponse],
    summary="판정 결과 조회",
    description="특정 분석에 대한 멘토 판정 결과를 조회합니다.",
    responses={
        404: {"model": ErrorResponse, "description": "판정 결과 없음 (JUDGE_003)"},
    },
)
async def get_judgment(
    analysisId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    judgment = await mentor_service.get_judgment(db, analysisId)
    return SuccessResponse(data=JudgmentResponse.model_validate(judgment))


# === Feedback ===

@router.post(
    "/feedback",
    response_model=SuccessResponse[FeedbackResponse],
    status_code=201,
    summary="피드백 작성 + 전송",
    description="멘티에게 날짜별 피드백을 작성합니다. 할 일별 세부 피드백(items)과 종합 코멘트를 포함합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "담당 멘티만 접근 가능"},
    },
)
async def create_feedback(
    data: FeedbackCreateRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    feedback = await mentor_service.create_feedback(db, current_user, data)
    return SuccessResponse(data=FeedbackResponse.model_validate(feedback))
