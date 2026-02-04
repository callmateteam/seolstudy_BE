import calendar
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.planner import CommentCreateRequest, CommentReplyRequest


def _date_to_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _calc_rate(tasks) -> float:
    if not tasks:
        return 0.0
    completed = sum(1 for t in tasks if t.status in ("SUBMITTED", "COMPLETED"))
    return round(completed / len(tasks), 2)


def _count_completed(tasks) -> int:
    return sum(1 for t in tasks if t.status in ("SUBMITTED", "COMPLETED"))


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

    total = len(tasks)
    completed = _count_completed(tasks)

    # 어제 피드백 존재 여부
    yesterday = planner_date - timedelta(days=1)
    yesterday_dt = _date_to_utc(yesterday)
    yesterday_feedback = await db.feedback.find_first(
        where={"menteeId": mentee_id, "date": yesterday_dt},
    )

    # 오늘 피드백 조회
    today_feedback_data = None
    today_feedback = await db.feedback.find_first(
        where={"menteeId": mentee_id, "date": dt},
        include={"mentor": {"include": {"user": True}}},
        order={"sentAt": "desc"},
    )
    if today_feedback:
        mentor_name = None
        if today_feedback.mentor and today_feedback.mentor.user:
            mentor_name = today_feedback.mentor.user.name
        fb_date = today_feedback.date
        if hasattr(fb_date, "date"):
            fb_date = fb_date.date()
        today_feedback_data = {
            "id": today_feedback.id,
            "date": fb_date,
            "summary": today_feedback.summary,
            "generalComment": today_feedback.generalComment,
            "isHighlighted": today_feedback.isHighlighted,
            "mentorName": mentor_name,
        }

    return {
        "date": planner_date,
        "tasks": tasks,
        "comments": comments,
        "completionRate": _calc_rate(tasks),
        "totalCount": total,
        "completedCount": completed,
        "hasYesterdayFeedback": yesterday_feedback is not None,
        "yesterdayFeedbackDate": yesterday if yesterday_feedback else None,
        "todayFeedback": today_feedback_data,
    }


async def get_completion_rate(db: Prisma, mentee_id: str, rate_date: date):
    dt = _date_to_utc(rate_date)
    tasks = await db.task.find_many(
        where={"menteeId": mentee_id, "date": dt}
    )
    total = len(tasks)
    completed = _count_completed(tasks)
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
        completed = _count_completed(tasks)
        days.append({
            "date": d,
            "total": total,
            "completed": completed,
            "rate": round(completed / total, 2) if total > 0 else 0.0,
        })

    return {"weekOf": monday, "days": days}


async def get_monthly(db: Prisma, mentee_id: str, year: int, month: int):
    _, last_day = calendar.monthrange(year, month)
    days = []

    for day in range(1, last_day + 1):
        d = date(year, month, day)
        dt = _date_to_utc(d)
        tasks = await db.task.find_many(
            where={"menteeId": mentee_id, "date": dt}
        )
        total = len(tasks)
        completed = _count_completed(tasks)
        days.append({
            "date": d,
            "total": total,
            "completed": completed,
            "rate": round(completed / total, 2) if total > 0 else 0.0,
        })

    return {"year": year, "month": month, "days": days}


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


async def reply_comment(db: Prisma, user, comment_id: str, data: CommentReplyRequest):
    if not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )

    comment = await db.dailycomment.find_unique(where={"id": comment_id})
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "COMMENT_002", "message": "코멘트를 찾을 수 없습니다"},
        )

    # 담당 멘티인지 검증
    relation = await db.mentormentee.find_first(
        where={
            "mentorId": user.mentorProfile.id,
            "menteeId": comment.menteeId,
        }
    )
    if not relation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "담당 멘티의 코멘트만 답변할 수 있습니다"},
        )

    updated = await db.dailycomment.update(
        where={"id": comment_id},
        data={
            "mentorReply": data.reply,
            "repliedAt": datetime.now(timezone.utc),
        },
    )
    return updated


async def get_yesterday_feedback(db: Prisma, mentee_id: str):
    yesterday = date.today() - timedelta(days=1)
    dt = _date_to_utc(yesterday)

    feedback = await db.feedback.find_first(
        where={"menteeId": mentee_id, "date": dt},
        include={"items": True},
        order={"sentAt": "desc"},
    )
    return feedback
