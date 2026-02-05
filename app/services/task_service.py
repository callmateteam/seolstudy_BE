from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from prisma import Json, Prisma

from app.schemas.task import (
    TaskCreateRequest,
    TaskProblemCreateRequest,
    TaskProblemUpdateRequest,
    TaskUpdateRequest,
)

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
        "tags": data.tags or [],
        "keyPoints": data.keyPoints,
        "content": data.content,
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


async def _create_problems_for_task(
    db: Prisma, task_id: str, problems: list[TaskProblemCreateRequest]
):
    for p in problems:
        data: dict = {
            "task": {"connect": {"id": task_id}},
            "number": p.number,
            "title": p.title,
            "content": p.content,
            "correctAnswer": p.correctAnswer,
            "displayOrder": p.displayOrder,
        }
        if p.options is not None:
            data["options"] = Json(p.options)
        await db.taskproblem.create(data=data)


def _task_to_response(task) -> dict:
    """Task DB 객체를 응답 dict로 변환 (problems 포함)."""
    problems = []
    if hasattr(task, "problems") and task.problems:
        problems = task.problems
    return {
        **{k: v for k, v in task.__dict__.items() if not k.startswith("_")},
        "problems": problems,
        "problemCount": len(problems),
    }


async def get_tasks(db: Prisma, mentee_id: str, task_date: date):
    tasks = await db.task.find_many(
        where={"menteeId": mentee_id, "date": _to_utc(task_date)},
        order={"displayOrder": "asc"},
        include={"problems": {"order_by": {"displayOrder": "asc"}}},
    )
    return [_task_to_response(t) for t in tasks]


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
    task = await db.task.create(data=task_data, include={"problems": True})

    if data.repeat and data.repeatDays:
        for rd in _get_repeat_dates(data.date, data.repeatDays):
            rd_data = _build_task_data(data, mentee_id, rd, False, "MENTEE", mentor_id)
            await db.task.create(data=rd_data)

    return _task_to_response(task)


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
    task = await db.task.create(data=task_data, include={"problems": True})

    if data.problems:
        await _create_problems_for_task(db, task.id, data.problems)
        task = await db.task.find_unique(
            where={"id": task.id},
            include={"problems": {"order_by": {"displayOrder": "asc"}}},
        )

    if data.repeat and data.repeatDays:
        for rd in _get_repeat_dates(data.date, data.repeatDays):
            rd_data = _build_task_data(data, mentee_id, rd, True, "MENTOR", user.mentorProfile.id)
            repeat_task = await db.task.create(data=rd_data)
            if data.problems:
                await _create_problems_for_task(db, repeat_task.id, data.problems)

    return _task_to_response(task)


async def get_task(db: Prisma, task_id: str):
    task = await db.task.find_unique(where={"id": task_id})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_002", "message": "할 일을 찾을 수 없습니다"},
        )
    return task


async def get_task_detail(db: Prisma, task_id: str):
    task = await db.task.find_unique(
        where={"id": task_id},
        include={
            "problems": {"order_by": {"displayOrder": "asc"}},
        },
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_002", "message": "할 일을 찾을 수 없습니다"},
        )
    return _task_to_response(task)


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
        return await get_task_detail(db, task_id)

    updated = await db.task.update(
        where={"id": task_id},
        data=update_data,
        include={"problems": {"order_by": {"displayOrder": "asc"}}},
    )
    return _task_to_response(updated)


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
        include={"problems": {"order_by": {"displayOrder": "asc"}}},
    )
    return _task_to_response(updated)


# ===== Bookmark =====

async def toggle_bookmark(db: Prisma, user, task_id: str, is_bookmarked: bool):
    task = await get_task(db, task_id)
    if not user.menteeProfile or task.menteeId != user.menteeProfile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "본인의 데이터만 접근 가능합니다"},
        )
    updated = await db.task.update(
        where={"id": task_id},
        data={"isBookmarked": is_bookmarked},
        include={"problems": {"order_by": {"displayOrder": "asc"}}},
    )
    return _task_to_response(updated)


# ===== Problem CRUD =====

async def _verify_mentor_for_task(db: Prisma, user, task_id: str):
    if not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 프로필이 없습니다"},
        )
    task = await get_task(db, task_id)
    link = await db.mentormentee.find_first(
        where={"mentorId": user.mentorProfile.id, "menteeId": task.menteeId}
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "담당 멘티의 데이터만 접근 가능합니다"},
        )
    return task


async def add_problem(db: Prisma, user, task_id: str, data: TaskProblemCreateRequest):
    await _verify_mentor_for_task(db, user, task_id)
    create_data: dict = {
        "task": {"connect": {"id": task_id}},
        "number": data.number,
        "title": data.title,
        "content": data.content,
        "correctAnswer": data.correctAnswer,
        "displayOrder": data.displayOrder,
    }
    if data.options is not None:
        create_data["options"] = Json(data.options)
    problem = await db.taskproblem.create(data=create_data)
    return problem


async def update_problem(
    db: Prisma, user, task_id: str, problem_id: str, data: TaskProblemUpdateRequest
):
    await _verify_mentor_for_task(db, user, task_id)
    problem = await db.taskproblem.find_first(
        where={"id": problem_id, "taskId": task_id}
    )
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_001", "message": "문제를 찾을 수 없습니다"},
        )
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return problem
    return await db.taskproblem.update(where={"id": problem_id}, data=update_data)


async def delete_problem(db: Prisma, user, task_id: str, problem_id: str):
    await _verify_mentor_for_task(db, user, task_id)
    problem = await db.taskproblem.find_first(
        where={"id": problem_id, "taskId": task_id}
    )
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_001", "message": "문제를 찾을 수 없습니다"},
        )
    await db.taskproblem.delete(where={"id": problem_id})
