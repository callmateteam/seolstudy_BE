from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from prisma import Prisma


def _date_to_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


async def get_feedback_by_date(db: Prisma, mentee_id: str, feedback_date: date):
    dt = _date_to_utc(feedback_date)
    feedbacks = await db.feedback.find_many(
        where={"menteeId": mentee_id, "date": dt},
        include={"items": True, "mentor": {"include": {"user": True}}},
        order={"sentAt": "desc"},
    )

    results = []
    for f in feedbacks:
        mentor_name = f.mentor.user.name if f.mentor and f.mentor.user else None
        results.append({
            "id": f.id,
            "menteeId": f.menteeId,
            "mentorId": f.mentorId,
            "date": f.date,
            "summary": f.summary,
            "isHighlighted": f.isHighlighted,
            "generalComment": f.generalComment,
            "items": f.items,
            "mentorName": mentor_name,
        })
    return results


async def get_feedback_by_subject(db: Prisma, mentee_id: str, subject: str):
    feedbacks = await db.feedback.find_many(
        where={"menteeId": mentee_id},
        include={
            "items": {
                "include": {
                    "task": {
                        "include": {
                            "submissions": {
                                "include": {"analysis": True}
                            }
                        }
                    }
                }
            },
            "mentor": {"include": {"user": True}},
        },
        order={"sentAt": "desc"},
    )

    results = []
    for f in feedbacks:
        subject_items = [item for item in f.items if item.task and item.task.subject == subject]
        if not subject_items:
            continue
        mentor_name = f.mentor.user.name if f.mentor and f.mentor.user else None

        enriched_items = []
        for item in subject_items:
            task = item.task
            task_date = task.date
            if hasattr(task_date, "date"):
                task_date = task_date.date()

            ai_summary = None
            signal_light = None
            density_score = None
            submission_id = None

            if task.submissions:
                latest = sorted(task.submissions, key=lambda s: s.submittedAt, reverse=True)[0]
                submission_id = latest.id
                if latest.analysis:
                    ai_summary = latest.analysis.summary
                    signal_light = latest.analysis.signalLight
                    density_score = latest.analysis.densityScore

            enriched_items.append({
                "id": item.id,
                "taskId": item.taskId,
                "detail": item.detail,
                "taskTitle": task.title,
                "taskDate": task_date,
                "aiSummary": ai_summary,
                "signalLight": signal_light,
                "densityScore": density_score,
                "submissionId": submission_id,
            })

        fb_date = f.date
        if hasattr(fb_date, "date"):
            fb_date = fb_date.date()

        results.append({
            "id": f.id,
            "date": fb_date,
            "summary": f.summary,
            "isHighlighted": f.isHighlighted,
            "generalComment": f.generalComment,
            "mentorName": mentor_name,
            "items": enriched_items,
        })
    return results


async def get_feedback_detail(db: Prisma, feedback_id: str):
    feedback = await db.feedback.find_unique(
        where={"id": feedback_id},
        include={"items": True, "mentor": {"include": {"user": True}}},
    )
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FEEDBACK_002", "message": "피드백을 찾을 수 없습니다"},
        )

    mentor_name = feedback.mentor.user.name if feedback.mentor and feedback.mentor.user else None
    return {
        "id": feedback.id,
        "menteeId": feedback.menteeId,
        "mentorId": feedback.mentorId,
        "date": feedback.date,
        "summary": feedback.summary,
        "isHighlighted": feedback.isHighlighted,
        "generalComment": feedback.generalComment,
        "items": feedback.items,
        "mentorName": mentor_name,
    }
