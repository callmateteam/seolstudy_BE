from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.planner import CommentCreateRequest


def _date_to_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _calc_rate(tasks) -> float:
    if not tasks:
        return 0.0
    completed = sum(1 for t in tasks if t.status in ("SUBMITTED", "COMPLETED"))
    return round(completed / len(tasks), 2)


async def get_planner(db: Prisma, mentee_id: str, planner_date: date):
    dt = _date_to_utc(planner_date)

    tasks = await db.task.find_many(
        where={"menteeId": mentee_id, "date": dt},
        order={"displayOrder": "asc"},
    )

    comments = await db.dailycomment.find_many(
        where={"menteeId": mentee_id, "date": dt},
        order={"createdAt": "asc"},
    )

    return {
        "date": planner_date,
        "tasks": tasks,
        "comments": comments,
        "completionRate": _calc_rate(tasks),
    }


async def get_completion_rate(db: Prisma, mentee_id: str, rate_date: date):
    dt = _date_to_utc(rate_date)
    tasks = await db.task.find_many(
        where={"menteeId": mentee_id, "date": dt}
    )
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status in ("SUBMITTED", "COMPLETED"))
    return {
        "date": rate_date,
        "total": total,
        "completed": completed,
        "rate": round(completed / total, 2) if total > 0 else 0.0,
    }


async def get_weekly(db: Prisma, mentee_id: str, week_of: date):
    monday = week_of - timedelta(days=week_of.weekday())
    days = []

    for i in range(7):
        d = monday + timedelta(days=i)
        dt = _date_to_utc(d)
        tasks = await db.task.find_many(
            where={"menteeId": mentee_id, "date": dt}
        )
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status in ("SUBMITTED", "COMPLETED"))
        days.append({
            "date": d,
            "total": total,
            "completed": completed,
            "rate": round(completed / total, 2) if total > 0 else 0.0,
        })

    return {"weekOf": monday, "days": days}


async def create_comment(db: Prisma, user, data: CommentCreateRequest):
    if not user.menteeProfile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "COMMENT_001", "message": "온보딩을 먼저 완료해주세요"},
        )

    comment = await db.dailycomment.create(
        data={
            "mentee": {"connect": {"id": user.menteeProfile.id}},
            "date": _date_to_utc(data.date),
            "content": data.content,
        }
    )
    return comment


async def get_comments(db: Prisma, mentee_id: str, comment_date: date):
    dt = _date_to_utc(comment_date)
    return await db.dailycomment.find_many(
        where={"menteeId": mentee_id, "date": dt},
        order={"createdAt": "asc"},
    )


async def get_yesterday_feedback(db: Prisma, mentee_id: str):
    yesterday = date.today() - timedelta(days=1)
    dt = _date_to_utc(yesterday)

    feedback = await db.feedback.find_first(
        where={"menteeId": mentee_id, "date": dt},
        include={"items": True},
        order={"sentAt": "desc"},
    )
    return feedback
