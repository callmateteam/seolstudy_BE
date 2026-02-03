from fastapi import APIRouter, Depends, status
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.submission import (
    SelfScoreRequest,
    SubmissionCreateRequest,
    SubmissionResponse,
)
from app.services import submission_service

router = APIRouter(tags=["Submissions"])


@router.post(
    "/api/tasks/{taskId}/submissions",
    response_model=SuccessResponse[SubmissionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="과제 제출",
    description="TEXT 모드는 textContent 입력, DRAWING 모드는 S3 이미지 URL 목록을 전달합니다. 제출 후 Task 상태가 SUBMITTED로 변경됩니다.",
    responses={
        400: {"model": ErrorResponse, "description": "입력값 오류 (SUBMIT_002)"},
        403: {"model": ErrorResponse, "description": "본인 데이터만 접근 가능 (PERM_002)"},
        404: {"model": ErrorResponse, "description": "할 일 없음 (TASK_002)"},
    },
)
async def create_submission(
    taskId: str,
    data: SubmissionCreateRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    submission = await submission_service.create_submission(db, current_user, taskId, data)
    return SuccessResponse(data=SubmissionResponse.model_validate(submission))


@router.get(
    "/api/tasks/{taskId}/submissions",
    response_model=SuccessResponse[list[SubmissionResponse]],
    summary="제출 내역 조회",
    description="특정 할 일의 제출 내역을 최신순으로 조회합니다.",
    responses={
        404: {"model": ErrorResponse, "description": "할 일 없음 (TASK_002)"},
    },
)
async def get_submissions(
    taskId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    submissions = await submission_service.get_submissions(db, taskId)
    return SuccessResponse(
        data=[SubmissionResponse.model_validate(s) for s in submissions]
    )


@router.put(
    "/api/submissions/{submissionId}/self-score",
    response_model=SuccessResponse[SubmissionResponse],
    summary="자기 채점",
    description="맞은 문제 수, 전체 문제 수, 틀린 문제 번호를 입력합니다. 멘티 본인만 가능합니다.",
    responses={
        400: {"model": ErrorResponse, "description": "채점 데이터 오류 (SUBMIT_004)"},
        403: {"model": ErrorResponse, "description": "본인 데이터만 접근 가능 (PERM_002)"},
        404: {"model": ErrorResponse, "description": "제출 내역 없음 (SUBMIT_003)"},
    },
)
async def update_self_score(
    submissionId: str,
    data: SelfScoreRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    submission = await submission_service.update_self_score(
        db, current_user, submissionId, data
    )
    return SuccessResponse(data=SubmissionResponse.model_validate(submission))
