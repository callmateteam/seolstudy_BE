from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.mentor import FeedbackCreateRequest, JudgmentModifyRequest


def _today_utc() -> datetime:
    t = date.today()
    return datetime(t.year, t.month, t.day, tzinfo=timezone.utc)


def _date_to_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


async def _require_mentor_profile(user):
    if user.role != "MENTOR" or not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )
    return user.mentorProfile


async def get_mentee_list(db: Prisma, user):
    profile = await _require_mentor_profile(user)
    links = await db.mentormentee.find_many(
        where={"mentorId": profile.id},
        include={"mentee": {"include": {"user": True}}},
        take=2,  # 멘토당 최대 2명
    )

    yesterday = date.today() - __import__("datetime").timedelta(days=1)
    yesterday_dt = _date_to_utc(yesterday)

    result = []
    for link in links:
        m = link.mentee

        # 전체 과제 완수율 계산
        all_tasks = await db.task.find_many(where={"menteeId": m.id})
        total = len(all_tasks)
        completed = sum(1 for t in all_tasks if t.status in ("SUBMITTED", "COMPLETED"))
        completion_rate = round((completed / total) * 100, 1) if total > 0 else 0.0

        # 어제 밀도 % (가장 최근 제출의 AI 분석)
        recent_density = None
        yesterday_submissions = await db.tasksubmission.find_many(
            where={
                "menteeId": m.id,
                "task": {"date": yesterday_dt},
            },
            include={"analysis": True},
            order={"submittedAt": "desc"},
            take=1,
        )
        if yesterday_submissions and yesterday_submissions[0].analysis:
            recent_density = yesterday_submissions[0].analysis.densityScore

        result.append({
            "menteeId": m.id,
            "name": m.user.name if m.user else "",
            "grade": m.grade,
            "subjects": m.subjects,
            "completionRate": completion_rate,
            "recentDensity": recent_density,
        })
    return result


async def get_mentee_detail(db: Prisma, user, mentee_id: str):
    profile = await _require_mentor_profile(user)
    link = await db.mentormentee.find_first(
        where={"mentorId": profile.id, "menteeId": mentee_id}
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "담당 멘티의 데이터만 접근 가능합니다"},
        )

    mentee = await db.menteeprofile.find_unique(
        where={"id": mentee_id},
        include={"user": True},
    )
    if not mentee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MENTOR_001", "message": "멘티를 찾을 수 없습니다"},
        )

    today = _today_utc()
    tasks = await db.task.find_many(
        where={"menteeId": mentee_id, "date": today},
        order={"displayOrder": "asc"},
    )
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status in ("SUBMITTED", "COMPLETED"))

    return {
        "menteeId": mentee.id,
        "name": mentee.user.name if mentee.user else "",
        "grade": mentee.grade,
        "subjects": mentee.subjects,
        "tasks": tasks,
        "completionRate": round(completed / total, 2) if total > 0 else 0.0,
    }


async def get_review_queue(db: Prisma, user):
    profile = await _require_mentor_profile(user)
    links = await db.mentormentee.find_many(where={"mentorId": profile.id})
    mentee_ids = [link.menteeId for link in links]

    if not mentee_ids:
        return []

    submissions = await db.tasksubmission.find_many(
        where={"menteeId": {"in": mentee_ids}},
        include={
            "task": True,
            "mentee": {"include": {"user": True}},
            "analysis": True,
        },
        order={"submittedAt": "desc"},
    )

    now = datetime.now(timezone.utc)
    queue = []
    for s in submissions:
        has_judgment = False
        if s.analysis:
            judgment = await db.mentorjudgment.find_unique(
                where={"analysisId": s.analysis.id}
            )
            if judgment:
                has_judgment = True

        if has_judgment:
            continue

        # 경과시간 계산 (분)
        elapsed = int((now - s.submittedAt.replace(tzinfo=timezone.utc)).total_seconds() / 60)

        queue.append({
            "submissionId": s.id,
            "taskId": s.taskId,
            "taskTitle": s.task.title if s.task else "",
            "menteeName": s.mentee.user.name if s.mentee and s.mentee.user else "",
            "menteeId": s.menteeId,
            "subject": s.task.subject if s.task else "",
            "abilityTag": s.task.abilityTag if s.task else None,
            "submittedAt": s.submittedAt,
            "elapsedMinutes": elapsed,
            "densityScore": s.analysis.densityScore if s.analysis else None,
        })

    # Sort: by submittedAt oldest first (오래된 것 먼저)
    queue.sort(key=lambda x: x["submittedAt"])
    return queue


async def get_comment_queue(db: Prisma, user):
    """코멘트 답변 대기열 조회"""
    profile = await _require_mentor_profile(user)
    links = await db.mentormentee.find_many(where={"mentorId": profile.id})
    mentee_ids = [link.menteeId for link in links]

    if not mentee_ids:
        return []

    comments = await db.dailycomment.find_many(
        where={"menteeId": {"in": mentee_ids}},
        include={"mentee": {"include": {"user": True}}},
        order={"createdAt": "desc"},
    )

    now = datetime.now(timezone.utc)
    queue = []
    for c in comments:
        # 경과시간 계산 (분)
        elapsed = int((now - c.createdAt.replace(tzinfo=timezone.utc)).total_seconds() / 60)

        queue.append({
            "commentId": c.id,
            "menteeId": c.menteeId,
            "menteeName": c.mentee.user.name if c.mentee and c.mentee.user else "",
            "content": c.content,
            "createdAt": c.createdAt,
            "elapsedMinutes": elapsed,
            "hasReply": c.mentorReply is not None,
        })

    return queue


async def get_dashboard(db: Prisma, user):
    mentees = await get_mentee_list(db, user)
    review_queue = await get_review_queue(db, user)
    comment_queue = await get_comment_queue(db, user)
    return {
        "mentees": mentees,
        "reviewQueue": review_queue,
        "commentQueue": comment_queue,
    }


async def confirm_judgment(db: Prisma, user, analysis_id: str):
    profile = await _require_mentor_profile(user)

    analysis = await db.aianalysis.find_unique(where={"id": analysis_id})
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JUDGE_001", "message": "분석 결과를 찾을 수 없습니다"},
        )

    existing = await db.mentorjudgment.find_unique(where={"analysisId": analysis_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "JUDGE_002", "message": "이미 판정이 완료되었습니다"},
        )

    judgment = await db.mentorjudgment.create(
        data={
            "analysis": {"connect": {"id": analysis_id}},
            "mentor": {"connect": {"id": profile.id}},
            "originalSignalLight": analysis.signalLight or "GREEN",
            "originalScore": analysis.densityScore or 0,
            "finalSignalLight": analysis.signalLight or "GREEN",
            "finalScore": analysis.densityScore or 0,
            "isModified": False,
        }
    )

    await db.aianalysis.update(
        where={"id": analysis_id},
        data={"status": "COMPLETED"},
    )

    return judgment


async def modify_judgment(
    db: Prisma, user, analysis_id: str, data: JudgmentModifyRequest
):
    profile = await _require_mentor_profile(user)

    analysis = await db.aianalysis.find_unique(where={"id": analysis_id})
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JUDGE_001", "message": "분석 결과를 찾을 수 없습니다"},
        )

    existing = await db.mentorjudgment.find_unique(where={"analysisId": analysis_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "JUDGE_002", "message": "이미 판정이 완료되었습니다"},
        )

    judgment = await db.mentorjudgment.create(
        data={
            "analysis": {"connect": {"id": analysis_id}},
            "mentor": {"connect": {"id": profile.id}},
            "originalSignalLight": analysis.signalLight or "GREEN",
            "originalScore": analysis.densityScore or 0,
            "finalSignalLight": data.signalLight,
            "finalScore": data.score,
            "reason": data.reason,
            "isModified": True,
        }
    )

    await db.aianalysis.update(
        where={"id": analysis_id},
        data={"status": "COMPLETED"},
    )

    return judgment


async def get_judgment(db: Prisma, analysis_id: str):
    judgment = await db.mentorjudgment.find_unique(where={"analysisId": analysis_id})
    if not judgment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JUDGE_003", "message": "판정 결과를 찾을 수 없습니다"},
        )
    return judgment


async def create_feedback(db: Prisma, user, data: FeedbackCreateRequest):
    profile = await _require_mentor_profile(user)

    link = await db.mentormentee.find_first(
        where={"mentorId": profile.id, "menteeId": data.menteeId}
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "담당 멘티의 데이터만 접근 가능합니다"},
        )

    feedback = await db.feedback.create(
        data={
            "mentee": {"connect": {"id": data.menteeId}},
            "mentor": {"connect": {"id": profile.id}},
            "date": _date_to_utc(data.date),
            "summary": data.summary,
            "isHighlighted": data.isHighlighted,
            "generalComment": data.generalComment,
            "items": {
                "create": [
                    {"taskId": item.taskId, "detail": item.detail}
                    for item in data.items
                ]
            },
        },
        include={"items": True},
    )

    return feedback


async def reply_to_comment(db: Prisma, user, comment_id: str, reply: str):
    """코멘트에 답변합니다."""
    profile = await _require_mentor_profile(user)

    comment = await db.dailycomment.find_unique(
        where={"id": comment_id},
        include={"mentee": True},
    )
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "COMMENT_001", "message": "코멘트를 찾을 수 없습니다"},
        )

    # 담당 멘티인지 확인
    link = await db.mentormentee.find_first(
        where={"mentorId": profile.id, "menteeId": comment.menteeId}
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "담당 멘티의 코멘트만 답변할 수 있습니다"},
        )

    updated = await db.dailycomment.update(
        where={"id": comment_id},
        data={
            "mentorReply": reply,
            "repliedAt": datetime.now(timezone.utc),
        },
    )

    return updated
