import datetime as dt

from fastapi import APIRouter, Depends, Query, UploadFile, status
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.lesson import (
    ABILITY_TAGS,
    AbilityTagsResponse,
    LessonCreateRequest,
    LessonListResponse,
    LessonResponse,
    LessonUpdateRequest,
    LessonUploadResponse,
)
from app.services import lesson_service, upload_service

router = APIRouter(prefix="/api/mentor/lessons", tags=["Lessons"])


@router.get(
    "/ability-tags",
    response_model=SuccessResponse[AbilityTagsResponse],
    summary="과목별 역량 태그 조회",
    description="과목에 해당하는 기본 역량 태그 목록을 반환합니다. 직접 입력도 가능합니다.",
)
async def get_ability_tags(
    subject: str = Query(pattern="^(KOREAN|ENGLISH|MATH)$", examples=["KOREAN"]),
):
    tags = lesson_service.get_ability_tags(subject)
    return SuccessResponse(data=AbilityTagsResponse(subject=subject, tags=tags))


@router.get(
    "/ability-tags/all",
    response_model=SuccessResponse[dict],
    summary="전체 과목 역량 태그 조회",
    description="모든 과목의 역량 태그 목록을 반환합니다.",
)
async def get_all_ability_tags():
    return SuccessResponse(data=ABILITY_TAGS)


@router.post(
    "",
    response_model=SuccessResponse[LessonResponse],
    status_code=status.HTTP_201_CREATED,
    summary="학습 등록",
    description="멘티에게 학습을 등록합니다. 역량 태그는 최대 3개까지 선택 가능합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "담당 멘티만 접근 가능"},
    },
)
async def create_lesson(
    data: LessonCreateRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await lesson_service.create_lesson(db, current_user, data)
    return SuccessResponse(data=LessonResponse(**result))


@router.get(
    "",
    response_model=SuccessResponse[LessonListResponse],
    summary="등록된 학습 조회",
    description="멘티의 특정 날짜 학습 목록을 조회합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "담당 멘티만 접근 가능"},
    },
)
async def get_lessons(
    menteeId: str = Query(..., description="멘티 ID"),
    date: dt.date = Query(..., description="날짜", examples=["2026-02-01"]),
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await lesson_service.get_lessons(db, current_user, menteeId, date)
    return SuccessResponse(data=LessonListResponse(**result))


@router.get(
    "/{lessonId}",
    response_model=SuccessResponse[LessonResponse],
    summary="학습 상세 조회",
    description="학습 상세 정보를 조회합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "담당 멘티만 접근 가능"},
        404: {"model": ErrorResponse, "description": "학습 없음"},
    },
)
async def get_lesson(
    lessonId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await lesson_service.get_lesson(db, current_user, lessonId)
    return SuccessResponse(data=LessonResponse(**result))


@router.patch(
    "/{lessonId}",
    response_model=SuccessResponse[LessonResponse],
    summary="학습 수정",
    description="학습 정보를 수정합니다.",
    responses={
        403: {"model": ErrorResponse, "description": "담당 멘티만 접근 가능"},
        404: {"model": ErrorResponse, "description": "학습 없음"},
    },
)
async def update_lesson(
    lessonId: str,
    data: LessonUpdateRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    result = await lesson_service.update_lesson(db, current_user, lessonId, data)
    return SuccessResponse(data=LessonResponse(**result))


@router.delete(
    "/{lessonId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="학습 삭제",
    description="학습을 삭제합니다. 제출이 있는 경우 삭제할 수 없습니다.",
    responses={
        403: {"model": ErrorResponse, "description": "담당 멘티만 접근 가능"},
        404: {"model": ErrorResponse, "description": "학습 없음"},
        409: {"model": ErrorResponse, "description": "제출이 있어 삭제 불가"},
    },
)
async def delete_lesson(
    lessonId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    await lesson_service.delete_lesson(db, current_user, lessonId)


@router.post(
    "/upload",
    response_model=SuccessResponse[LessonUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="학습지 업로드",
    description="PDF 학습지를 업로드합니다. 향후 지문/문제 분리 기능이 추가될 예정입니다.",
    responses={
        400: {"model": ErrorResponse, "description": "파일 형식 또는 크기 오류"},
    },
)
async def upload_lesson_material(
    file: UploadFile,
    current_user=Depends(get_current_user),
):
    # 멘토 권한 확인
    if current_user.role != "MENTOR":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )

    result = await upload_service.upload_pdf(file)

    # TODO: OCR/AI를 통한 지문/문제 분리
    # 현재는 업로드만 수행하고, 파싱 기능은 향후 구현

    return SuccessResponse(
        data=LessonUploadResponse(
            materialUrl=result["url"],
            originalName=result["originalName"],
            size=result["size"],
            parsed=False,
            content=None,
            problems=None,
        )
    )
