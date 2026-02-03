from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.task import TaskCreateRequest, TaskUpdateRequest


async def get_tasks(db: Prisma, mentee_id: str, task_date: date):
    return await db.task.find_many(
        where={
            "menteeId": mentee_id,
            "date": datetime(task_date.year, task_date.month, task_date.day, tzinfo=timezone.utc),
        },
        order={"displayOrder": "asc"},
    )


async def create_task(db: Prisma, user, data: TaskCreateRequest):
    is_mentor = user.role == "MENTOR"
    is_mentee = user.role == "MENTEE"

    if is_mentee:
        if not user.menteeProfile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "TASK_001", "message": "온보딩을 먼저 완료해주세요"},
            )
        mentee_id = user.menteeProfile.id
        created_by_mentor_id = None
    elif is_mentor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TASK_001", "message": "멘토는 menteeId를 지정해야 합니다"},
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "접근 권한이 없습니다"},
        )

    task = await db.task.create(
        data={
            "mentee": {"connect": {"id": mentee_id}},
            "date": datetime(data.date.year, data.date.month, data.date.day, tzinfo=timezone.utc),
            "title": data.title,
            "goal": data.goal,
            "subject": data.subject,
            "abilityTag": data.abilityTag,
            "materialType": data.materialType,
            "materialId": data.materialId,
            "materialUrl": data.materialUrl,
            "isLocked": False,
            "createdBy": "MENTEE",
            "createdByMentorId": created_by_mentor_id,
            "displayOrder": data.displayOrder,
        }
    )
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

    task = await db.task.create(
        data={
            "mentee": {"connect": {"id": mentee_id}},
            "date": datetime(data.date.year, data.date.month, data.date.day, tzinfo=timezone.utc),
            "title": data.title,
            "goal": data.goal,
            "subject": data.subject,
            "abilityTag": data.abilityTag,
            "materialType": data.materialType,
            "materialId": data.materialId,
            "materialUrl": data.materialUrl,
            "isLocked": True,
            "createdBy": "MENTOR",
            "createdByMentorId": user.mentorProfile.id,
            "displayOrder": data.displayOrder,
        }
    )
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
