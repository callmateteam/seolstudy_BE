from fastapi import APIRouter, BackgroundTasks, Depends
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.analysis import AnalysisResponse, AnalysisStatusResponse, AnalysisTriggerResponse
from app.schemas.common import ErrorResponse, SuccessResponse
from app.services import analysis_service

router = APIRouter(prefix="/api/analysis", tags=["AI Analysis"])


@router.post(
    "/{submissionId}/trigger",
    response_model=SuccessResponse[AnalysisTriggerResponse],
    status_code=201,
    summary="AI 분석 시작",
    description="제출물에 대한 AI 밀도 분석을 시작합니다. 제출 시 자동 호출되거나 수동 호출 가능합니다.",
    responses={
        404: {"model": ErrorResponse, "description": "제출물 없음 (ANALYSIS_003)"},
    },
)
async def trigger_analysis(
    submissionId: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await analysis_service.trigger_analysis(db, submissionId)
    if result["status"] == "PROCESSING":
        background_tasks.add_task(
            analysis_service.run_analysis_background, db, result["analysisId"]
        )
    return SuccessResponse(data=AnalysisTriggerResponse(**result))


@router.get(
    "/{submissionId}",
    response_model=SuccessResponse[AnalysisResponse],
    summary="분석 결과 조회",
    description="특정 제출물의 AI 분석 결과를 조회합니다.",
    responses={
        404: {"model": ErrorResponse, "description": "분석 결과 없음 (ANALYSIS_003)"},
    },
)
async def get_analysis(
    submissionId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    analysis = await analysis_service.get_analysis(db, submissionId)
    return SuccessResponse(data=AnalysisResponse.model_validate(analysis))


@router.get(
    "/{submissionId}/status",
    response_model=SuccessResponse[AnalysisStatusResponse],
    summary="분석 상태 확인",
    description="분석 진행 상태를 폴링합니다. (프론트: 5초 간격 권장)",
    responses={
        404: {"model": ErrorResponse, "description": "분석 결과 없음 (ANALYSIS_003)"},
    },
)
async def get_analysis_status(
    submissionId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await analysis_service.get_analysis_status(db, submissionId)
    return SuccessResponse(data=AnalysisStatusResponse(**result))


@router.post(
    "/{submissionId}/retry",
    response_model=SuccessResponse[AnalysisTriggerResponse],
    summary="분석 재시도",
    description="실패한 분석을 재시도합니다. FAILED 상태에서만 가능합니다.",
    responses={
        400: {"model": ErrorResponse, "description": "재시도 불가 (ANALYSIS_001)"},
        404: {"model": ErrorResponse, "description": "분석 결과 없음 (ANALYSIS_003)"},
    },
)
async def retry_analysis(
    submissionId: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await analysis_service.retry_analysis(db, submissionId)
    background_tasks.add_task(
        analysis_service.run_analysis_background, db, result["analysisId"]
    )
    return SuccessResponse(data=AnalysisTriggerResponse(**result))
