from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.task import TaskCreateRequest, TaskUpdateRequest

DAY_MAP = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}


def _to_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _build_task_data(data: TaskCreateRequest, mentee_id: str, task_date: date,
                     is_locked: bool, created_by: str, mentor_id: str | None) -> dict:
    return {
        "mentee": {"connect": {"id": mentee_id}},
        "date": _to_utc(task_date),
        "title": data.title,
        "goal": data.goal,
        "subject": data.subject,
        "abilityTag": data.abilityTag,
        "materialType": data.materialType,
        "materialId": data.materialId,
        "materialUrl": data.materialUrl,
        "isLocked": is_locked,
        "createdBy": created_by,
        "createdByMentorId": mentor_id,
        "repeat": data.repeat,
        "repeatDays": data.repeatDays or [],
        "targetStudyMinutes": data.targetStudyMinutes,
        "memo": data.memo,
        "displayOrder": data.displayOrder,
    }


def _get_repeat_dates(base_date: date, repeat_days: list[str]) -> list[date]:
    """base_date가 속한 주(월~일)에서 repeat_days에 해당하는 날짜들을 반환 (base_date 제외)."""
    monday = base_date - timedelta(days=base_date.weekday())
    dates = []
    for day_name in repeat_days:
        offset = DAY_MAP.get(day_name)
        if offset is None:
            continue
        d = monday + timedelta(days=offset)
        if d != base_date:
            dates.append(d)
    return sorted(dates)


async def get_tasks(db: Prisma, mentee_id: str, task_date: date):
    return await db.task.find_many(
        where={"menteeId": mentee_id, "date": _to_utc(task_date)},
        order={"displayOrder": "asc"},
    )


async def create_task(db: Prisma, user, data: TaskCreateRequest):
    if user.role == "MENTEE":
        if not user.menteeProfile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "TASK_001", "message": "온보딩을 먼저 완료해주세요"},
            )
        mentee_id = user.menteeProfile.id
        mentor_id = None
    elif user.role == "MENTOR":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TASK_001", "message": "멘토는 menteeId를 지정해야 합니다"},
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "접근 권한이 없습니다"},
        )

    task_data = _build_task_data(data, mentee_id, data.date, False, "MENTEE", mentor_id)
    task = await db.task.create(data=task_data)

    if data.repeat and data.repeatDays:
        for rd in _get_repeat_dates(data.date, data.repeatDays):
            rd_data = _build_task_data(data, mentee_id, rd, False, "MENTEE", mentor_id)
            await db.task.create(data=rd_data)

    return task


async def create_task_by_mentor(
    db: Prisma, user, mentee_id: str, data: TaskCreateRequest
):
    if not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TASK_001", "message": "온보딩을 먼저 완료해주세요"},
        )

    link = await db.mentormentee.find_first(
        where={"mentorId": user.mentorProfile.id, "menteeId": mentee_id}
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "담당 멘티의 데이터만 접근 가능합니다"},
        )

    task_data = _build_task_data(data, mentee_id, data.date, True, "MENTOR", user.mentorProfile.id)
    task = await db.task.create(data=task_data)

    if data.repeat and data.repeatDays:
        for rd in _get_repeat_dates(data.date, data.repeatDays):
            rd_data = _build_task_data(data, mentee_id, rd, True, "MENTOR", user.mentorProfile.id)
            await db.task.create(data=rd_data)

    return task


async def get_task(db: Prisma, task_id: str):
    task = await db.task.find_unique(where={"id": task_id})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_002", "message": "할 일을 찾을 수 없습니다"},
        )
    return task


async def update_task(db: Prisma, user, task_id: str, data: TaskUpdateRequest):
    task = await get_task(db, task_id)

    if user.role == "MENTEE":
        if not user.menteeProfile or task.menteeId != user.menteeProfile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_002", "message": "본인의 데이터만 접근 가능합니다"},
            )
        if task.isLocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "TASK_003", "message": "멘토가 생성한 할 일은 수정할 수 없습니다"},
            )
    elif user.role == "MENTOR":
        if not user.mentorProfile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_001", "message": "멘토 프로필이 없습니다"},
            )
        link = await db.mentormentee.find_first(
            where={"mentorId": user.mentorProfile.id, "menteeId": task.menteeId}
        )
        if not link:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_002", "message": "담당 멘티의 데이터만 접근 가능합니다"},
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "접근 권한이 없습니다"},
        )

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return task

    updated = await db.task.update(where={"id": task_id}, data=update_data)
    return updated


async def delete_task(db: Prisma, user, task_id: str):
    task = await get_task(db, task_id)

    if user.role == "MENTEE":
        if not user.menteeProfile or task.menteeId != user.menteeProfile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_002", "message": "본인의 데이터만 접근 가능합니다"},
            )
        if task.isLocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "TASK_003", "message": "멘토가 생성한 할 일은 삭제할 수 없습니다"},
            )
    elif user.role == "MENTOR":
        if not user.mentorProfile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_001", "message": "멘토 프로필이 없습니다"},
            )
        link = await db.mentormentee.find_first(
            where={"mentorId": user.mentorProfile.id, "menteeId": task.menteeId}
        )
        if not link:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_002", "message": "담당 멘티의 데이터만 접근 가능합니다"},
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "접근 권한이 없습니다"},
        )

    await db.task.delete(where={"id": task_id})


async def update_study_time(db: Prisma, user, task_id: str, minutes: int):
    task = await get_task(db, task_id)

    if not user.menteeProfile or task.menteeId != user.menteeProfile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "본인의 데이터만 접근 가능합니다"},
        )

    updated = await db.task.update(
        where={"id": task_id},
        data={"studyTimeMinutes": minutes},
    )
    return updated
