from datetime import datetime, timezone

from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.lesson import (
    ABILITY_TAGS,
    LessonCreateRequest,
    LessonUpdateRequest,
)


def _date_to_utc(d) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


async def _require_mentor_profile(user):
    if user.role != "MENTOR" or not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )
    return user.mentorProfile


async def _verify_mentee_access(db: Prisma, mentor_profile_id: str, mentee_id: str):
    """담당 멘티인지 확인"""
    link = await db.mentormentee.find_first(
        where={"mentorId": mentor_profile_id, "menteeId": mentee_id}
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "담당 멘티만 접근 가능합니다"},
        )


def get_ability_tags(subject: str) -> list[str]:
    """과목별 역량 태그 목록을 반환합니다."""
    if subject not in ABILITY_TAGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "LESSON_001", "message": f"유효하지 않은 과목: {subject}"},
        )
    return ABILITY_TAGS[subject]


async def create_lesson(db: Prisma, user, data: LessonCreateRequest):
    """학습을 등록합니다."""
    profile = await _require_mentor_profile(user)
    await _verify_mentee_access(db, profile.id, data.menteeId)

    # 역량 태그 검증 (최대 3개)
    if len(data.abilityTags) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "LESSON_002", "message": "역량 태그는 최대 3개까지 가능합니다"},
        )

    task = await db.task.create(
        data={
            "menteeId": data.menteeId,
            "createdByMentorId": profile.id,
            "date": _date_to_utc(data.date),
            "title": data.title,
            "goal": data.goal,
            "subject": data.subject,
            "abilityTag": data.abilityTags[0] if data.abilityTags else None,
            "tags": data.abilityTags,
            "materialId": data.materialId,
            "materialUrl": data.materialUrl,
            "materialType": "PDF" if data.materialUrl or data.materialId else None,
            "createdBy": "MENTOR",
            "status": "PENDING",
        }
    )

    return _task_to_lesson_response(task)


async def get_lessons(
    db: Prisma,
    user,
    mentee_id: str,
    date,
):
    """멘티의 특정 날짜 학습 목록을 조회합니다."""
    profile = await _require_mentor_profile(user)
    await _verify_mentee_access(db, profile.id, mentee_id)

    tasks = await db.task.find_many(
        where={
            "menteeId": mentee_id,
            "date": _date_to_utc(date),
            "createdBy": "MENTOR",
        },
        order={"createdAt": "desc"},
    )

    return {
        "lessons": [_task_to_lesson_response(t) for t in tasks],
        "total": len(tasks),
    }


async def get_lesson(db: Prisma, user, lesson_id: str):
    """학습 상세를 조회합니다."""
    profile = await _require_mentor_profile(user)

    task = await db.task.find_unique(where={"id": lesson_id})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LESSON_003", "message": "학습을 찾을 수 없습니다"},
        )

    await _verify_mentee_access(db, profile.id, task.menteeId)

    return _task_to_lesson_response(task)


async def update_lesson(db: Prisma, user, lesson_id: str, data: LessonUpdateRequest):
    """학습을 수정합니다."""
    profile = await _require_mentor_profile(user)

    task = await db.task.find_unique(where={"id": lesson_id})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LESSON_003", "message": "학습을 찾을 수 없습니다"},
        )

    await _verify_mentee_access(db, profile.id, task.menteeId)

    # 역량 태그 검증
    if data.abilityTags and len(data.abilityTags) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "LESSON_002", "message": "역량 태그는 최대 3개까지 가능합니다"},
        )

    update_data = {}
    if data.subject is not None:
        update_data["subject"] = data.subject
    if data.abilityTags is not None:
        update_data["tags"] = data.abilityTags
        update_data["abilityTag"] = data.abilityTags[0] if data.abilityTags else None
    if data.title is not None:
        update_data["title"] = data.title
    if data.goal is not None:
        update_data["goal"] = data.goal
    if data.materialId is not None:
        update_data["materialId"] = data.materialId
    if data.materialUrl is not None:
        update_data["materialUrl"] = data.materialUrl

    if update_data:
        task = await db.task.update(
            where={"id": lesson_id},
            data=update_data,
        )

    return _task_to_lesson_response(task)


async def delete_lesson(db: Prisma, user, lesson_id: str):
    """학습을 삭제합니다."""
    profile = await _require_mentor_profile(user)

    task = await db.task.find_unique(where={"id": lesson_id})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LESSON_003", "message": "학습을 찾을 수 없습니다"},
        )

    await _verify_mentee_access(db, profile.id, task.menteeId)

    # 제출이 있으면 삭제 불가
    submissions = await db.tasksubmission.find_many(where={"taskId": lesson_id})
    if submissions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "LESSON_004", "message": "제출이 있는 학습은 삭제할 수 없습니다"},
        )

    await db.task.delete(where={"id": lesson_id})


def _task_to_lesson_response(task):
    """Task를 LessonResponse 형식으로 변환"""
    return {
        "id": task.id,
        "menteeId": task.menteeId,
        "date": task.date.date() if hasattr(task.date, "date") else task.date,
        "subject": task.subject,
        "abilityTags": task.tags or [],
        "title": task.title,
        "goal": task.goal,
        "materialId": task.materialId,
        "materialUrl": task.materialUrl,
        "status": task.status,
        "createdAt": task.createdAt,
    }
