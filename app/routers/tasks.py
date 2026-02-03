from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.task import (
    StudyTimeRequest,
    TaskCreateRequest,
    TaskResponse,
    TaskUpdateRequest,
)
from app.services import task_service

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get(
    "",
    response_model=SuccessResponse[list[TaskResponse]],
    summary="할 일 목록 조회",
    description="날짜별 할 일 목록을 조회합니다. 멘티는 본인, 멘토는 담당 멘티의 할 일을 조회합니다.",
    responses={
        401: {"model": ErrorResponse, "description": "인증 실패"},
    },
)
async def get_tasks(
    date: date = Query(..., description="조회 날짜 (YYYY-MM-DD)", examples=["2026-02-03"]),
    menteeId: str | None = Query(default=None, description="멘티 ID (멘토 전용)"),
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    if current_user.role == "MENTEE":
        if not current_user.menteeProfile:
            return SuccessResponse(data=[])
        target_mentee_id = current_user.menteeProfile.id
    elif current_user.role == "MENTOR":
        if not menteeId:
            return SuccessResponse(data=[])
        target_mentee_id = menteeId
    else:
        return SuccessResponse(data=[])

    tasks = await task_service.get_tasks(db, target_mentee_id, date)
    return SuccessResponse(
        data=[TaskResponse.model_validate(t) for t in tasks]
    )


@router.post(
    "",
    response_model=SuccessResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
    summary="할 일 생성",
    description="새 할 일을 생성합니다. 멘티가 직접 생성하거나, 멘토가 menteeId를 지정하여 생성합니다. 멘토 생성 시 isLocked=true.",
    responses={
        400: {"model": ErrorResponse, "description": "온보딩 미완료 (TASK_001)"},
        403: {"model": ErrorResponse, "description": "권한 없음"},
    },
)
async def create_task(
    data: TaskCreateRequest,
    menteeId: str | None = Query(default=None, description="멘티 ID (멘토 전용)"),
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    if current_user.role == "MENTOR" and menteeId:
        task = await task_service.create_task_by_mentor(db, current_user, menteeId, data)
    else:
        task = await task_service.create_task(db, current_user, data)
    return SuccessResponse(data=TaskResponse.model_validate(task))


@router.get(
    "/{taskId}",
    response_model=SuccessResponse[TaskResponse],
    summary="할 일 상세 조회",
    description="특정 할 일의 상세 정보를 조회합니다.",
    responses={
        404: {"model": ErrorResponse, "description": "할 일 없음 (TASK_002)"},
    },
)
async def get_task(
    taskId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    task = await task_service.get_task(db, taskId)
    return SuccessResponse(data=TaskResponse.model_validate(task))


@router.put(
    "/{taskId}",
    response_model=SuccessResponse[TaskResponse],
    summary="할 일 수정",
    description="할 일을 수정합니다. 멘티는 본인이 만든 unlocked 항목만, 멘토는 담당 멘티의 할 일을 수정합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "잠긴 할 일 수정 불가 (TASK_003)"},
        404: {"model": ErrorResponse, "description": "할 일 없음 (TASK_002)"},
    },
)
async def update_task(
    taskId: str,
    data: TaskUpdateRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    task = await task_service.update_task(db, current_user, taskId, data)
    return SuccessResponse(data=TaskResponse.model_validate(task))


@router.delete(
    "/{taskId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="할 일 삭제",
    description="할 일을 삭제합니다. 멘티는 본인이 만든 unlocked 항목만, 멘토는 담당 멘티의 할 일을 삭제합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "잠긴 할 일 삭제 불가 (TASK_003)"},
        404: {"model": ErrorResponse, "description": "할 일 없음 (TASK_002)"},
    },
)
async def delete_task(
    taskId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    await task_service.delete_task(db, current_user, taskId)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{taskId}/study-time",
    response_model=SuccessResponse[TaskResponse],
    summary="공부 시간 기록",
    description="해당 할 일의 공부 시간을 분 단위로 기록합니다. 멘티 본인만 가능합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "본인 데이터만 접근 가능 (PERM_002)"},
        404: {"model": ErrorResponse, "description": "할 일 없음 (TASK_002)"},
    },
)
async def update_study_time(
    taskId: str,
    data: StudyTimeRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    task = await task_service.update_study_time(db, current_user, taskId, data.minutes)
    return SuccessResponse(data=TaskResponse.model_validate(task))
