from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.parent import MentorBasicInfo


def _today_utc() -> datetime:
    t = date.today()
    return datetime(t.year, t.month, t.day, tzinfo=timezone.utc)


def _date_to_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


async def _require_parent(user, db: Prisma):
    if user.role != "PARENT" or not user.parentProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "학부모 권한이 필요합니다"},
        )

    mentee = await db.menteeprofile.find_unique(
        where={"id": user.parentProfile.menteeId},
        include={"user": True},
    )
    if not mentee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PARENT_001", "message": "연결된 자녀를 찾을 수 없습니다"},
        )
    return user.parentProfile, mentee


async def get_dashboard(db: Prisma, user):
    parent_profile, mentee = await _require_parent(user, db)

    today = _today_utc()
    tasks = await db.task.find_many(where={"menteeId": mentee.id, "date": today})
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status in ("SUBMITTED", "COMPLETED"))

    # Find mentor with avatar
    link = await db.mentormentee.find_first(
        where={"menteeId": mentee.id},
        include={"mentor": {"include": {"user": True}}},
    )
    mentor_info = None
    if link and link.mentor and link.mentor.user:
        mentor_info = MentorBasicInfo(
            id=link.mentor.id,
            name=link.mentor.user.name,
            avatar=link.mentor.user.avatar or 1,
            university=link.mentor.university or "",
            department=link.mentor.department or "",
        )

    # Recent feedback count (last 7 days)
    week_ago = today - timedelta(days=7)
    feedbacks = await db.feedback.find_many(
        where={"menteeId": mentee.id, "date": {"gte": week_ago}},
    )

    # Calculate weekly density score from AI analysis
    monday = today - timedelta(days=today.weekday())
    week_submissions = await db.tasksubmission.find_many(
        where={
            "task": {"menteeId": mentee.id, "date": {"gte": monday}},
        },
        include={"analysis": True},
    )
    density_scores = []
    for sub in week_submissions:
        if sub.analysis and sub.analysis.densityScore is not None:
            density_scores.append(sub.analysis.densityScore)
    weekly_density = (
        round(sum(density_scores) / len(density_scores), 1)
        if density_scores
        else None
    )

    return {
        "menteeName": mentee.user.name if mentee.user else "",
        "menteeGrade": mentee.grade,
        "menteeSubjects": mentee.subjects,
        "todayTaskCount": total,
        "todayCompletedCount": completed,
        "todayCompletionRate": round(completed / total, 2) if total > 0 else 0.0,
        "weeklyDensityScore": weekly_density,
        "mentor": mentor_info,
        "recentFeedbackCount": len(feedbacks),
    }


async def get_mentee_status(db: Prisma, user):
    parent_profile, mentee = await _require_parent(user, db)

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    monday_dt = _date_to_utc(monday)
    weekly_rates = []
    total_week = 0
    completed_week = 0

    for i in range(7):
        d = monday + timedelta(days=i)
        dt = _date_to_utc(d)
        tasks = await db.task.find_many(where={"menteeId": mentee.id, "date": dt})
        t = len(tasks)
        c = sum(1 for task in tasks if task.status in ("SUBMITTED", "COMPLETED"))
        total_week += t
        completed_week += c
        weekly_rates.append({
            "date": str(d),
            "total": t,
            "completed": c,
            "rate": round(c / t, 2) if t > 0 else 0.0,
        })

    # Calculate weekly density score from AI analysis
    week_submissions = await db.tasksubmission.find_many(
        where={
            "task": {"menteeId": mentee.id, "date": {"gte": monday_dt}},
        },
        include={"analysis": True},
    )
    density_scores = []
    for sub in week_submissions:
        if sub.analysis and sub.analysis.densityScore is not None:
            density_scores.append(sub.analysis.densityScore)
    weekly_density = (
        round(sum(density_scores) / len(density_scores), 1)
        if density_scores
        else None
    )

    return {
        "weeklyCompletionRates": weekly_rates,
        "totalTasksThisWeek": total_week,
        "completedTasksThisWeek": completed_week,
        "weeklyDensityScore": weekly_density,
    }


async def get_mentor_info(db: Prisma, user):
    parent_profile, mentee = await _require_parent(user, db)

    link = await db.mentormentee.find_first(
        where={"menteeId": mentee.id},
        include={"mentor": {"include": {"user": True}}},
    )

    if not link or not link.mentor:
        return {
            "mentorId": None,
            "mentorName": None,
            "avatar": 1,
            "university": None,
            "department": None,
            "subjects": [],
            "recentFeedbackCount": 0,
        }

    mentor = link.mentor
    week_ago = _today_utc() - timedelta(days=7)
    feedbacks = await db.feedback.find_many(
        where={
            "menteeId": mentee.id,
            "mentorId": mentor.id,
            "date": {"gte": week_ago},
        }
    )

    return {
        "mentorId": mentor.id,
        "mentorName": mentor.user.name if mentor.user else None,
        "avatar": mentor.user.avatar if mentor.user else 1,
        "university": mentor.university,
        "department": mentor.department,
        "subjects": mentor.subjects,
        "recentFeedbackCount": len(feedbacks),
    }
