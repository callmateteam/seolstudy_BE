from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.coaching import (
    AssignMaterialRequest,
    DailySummaryRequest,
    TaskFeedbackRequest,
)


async def get_coaching_detail(db: Prisma, user, submission_id: str):
    if not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )

    submission = await db.tasksubmission.find_unique(
        where={"id": submission_id},
        include={
            "analysis": True,
            "task": {"include": {"mentee": {"include": {"user": True}}}},
        },
    )
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUBMIT_003", "message": "제출 내역을 찾을 수 없습니다"},
        )

    return {
        "submission": submission,
        "analysis": submission.analysis,
        "taskTitle": submission.task.title if submission.task else "",
        "menteeName": submission.task.mentee.user.name if submission.task and submission.task.mentee else "",
    }


async def get_ai_draft(db: Prisma, user, submission_id: str):
    if not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )

    submission = await db.tasksubmission.find_unique(
        where={"id": submission_id},
        include={"analysis": True, "task": True},
    )
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUBMIT_003", "message": "제출 내역을 찾을 수 없습니다"},
        )

    analysis = submission.analysis
    if not analysis or analysis.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ANALYSIS_001", "message": "분석이 아직 완료되지 않았습니다"},
        )

    signal = analysis.signalLight or "YELLOW"
    score = analysis.densityScore or 50
    task_title = submission.task.title if submission.task else ""

    drafts = {
        "GREEN": f"'{task_title}' 과제의 학습 밀도가 높습니다(점수: {score}). 풀이 흔적이 충분하고 이해도가 높아 보입니다. 이 조자로 계속 학습하면 좋겠습니다.",
        "YELLOW": f"'{task_title}' 과제의 학습 밀도가 보통입니다(점수: {score}). 일부 풀이 과정이 생략된 부분이 있어 보충이 필요합니다.",
        "RED": f"'{task_title}' 과제의 학습 밀도가 낮습니다(점수: {score}). 풀이 흔적이 부족하여 다시 한번 꼼꼼히 학습해 주세요.",
    }

    return {
        "submissionId": submission_id,
        "draft": drafts.get(signal, drafts["YELLOW"]),
        "suggestedSignalLight": signal,
        "suggestedScore": score,
    }


async def get_recommendations(db: Prisma, user, submission_id: str):
    if not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )

    submission = await db.tasksubmission.find_unique(
        where={"id": submission_id},
        include={"task": True},
    )
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUBMIT_003", "message": "제출 내역을 찾을 수 없습니다"},
        )

    subject = submission.task.subject if submission.task else None
    ability_tag = submission.task.abilityTag if submission.task else None

    where: dict = {}
    if subject:
        where["subject"] = subject

    materials = await db.material.find_many(
        where=where,
        take=5,
        order={"createdAt": "desc"},
    )

    recs = []
    for m in materials:
        tag_match = ability_tag and ability_tag in m.abilityTags
        reason = f"과목 일치({subject})"
        if tag_match:
            reason += f", 능력 태그 일치({ability_tag})"
        recs.append({
            "materialId": m.id,
            "title": m.title,
            "subject": m.subject,
            "abilityTags": m.abilityTags,
            "difficulty": m.difficulty,
            "reason": reason,
        })

    return {"submissionId": submission_id, "recommendations": recs}


async def assign_material(db: Prisma, user, data: AssignMaterialRequest):
    if not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )

    material = await db.material.find_unique(where={"id": data.materialId})
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MATERIAL_001", "message": "학습지를 찾을 수 없습니다"},
        )

    mentee_link = await db.mentormentee.find_first(
        where={"mentorId": user.mentorProfile.id, "menteeId": data.menteeId}
    )
    if not mentee_link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "담당 멘티만 접근 가능합니다"},
        )

    task_date = datetime.strptime(data.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    title = data.title or f"[보완] {material.title}"

    task = await db.task.create(
        data={
            "mentee": {"connect": {"id": data.menteeId}},
            "createdByMentorId": user.mentorProfile.id,
            "date": task_date,
            "title": title,
            "subject": material.subject,
            "materialType": material.type,
            "materialId": material.id,
            "materialUrl": material.contentUrl,
            "isLocked": True,
            "createdBy": "MENTOR",
        }
    )
    return task


def _to_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


async def _verify_mentor_mentee(db: Prisma, user, mentee_id: str):
    """멘토-멘티 관계 확인"""
    if not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )
    link = await db.mentormentee.find_first(
        where={"mentorId": user.mentorProfile.id, "menteeId": mentee_id}
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_002", "message": "담당 멘티만 접근 가능합니다"},
        )
    return user.mentorProfile


def _generate_ai_draft(analysis, task_title: str) -> str:
    """AI 피드백 초안 생성"""
    if not analysis or analysis.status != "COMPLETED":
        return None

    signal = analysis.signalLight or "YELLOW"
    score = analysis.densityScore or 50

    drafts = {
        "GREEN": f"'{task_title}' 과제의 학습 밀도가 높습니다(점수: {score}). 풀이 흔적이 충분하고 이해도가 높아 보입니다. 이 조자로 계속 학습하면 좋겠습니다.",
        "YELLOW": f"'{task_title}' 과제의 학습 밀도가 보통입니다(점수: {score}). 일부 풀이 과정이 생략된 부분이 있어 보충이 필요합니다.",
        "RED": f"'{task_title}' 과제의 학습 밀도가 낮습니다(점수: {score}). 풀이 흔적이 부족하여 다시 한번 꼼꼼히 학습해 주세요.",
    }
    return drafts.get(signal, drafts["YELLOW"])


async def get_coaching_session(
    db: Prisma, user, mentee_id: str, session_date: date
):
    """코칭센터 세션 종합 조회"""
    mentor_profile = await _verify_mentor_mentee(db, user, mentee_id)

    # 멘티 정보
    mentee = await db.menteeprofile.find_unique(
        where={"id": mentee_id},
        include={"user": True},
    )
    if not mentee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MENTEE_001", "message": "멘티를 찾을 수 없습니다"},
        )

    # 해당 날짜의 과제 목록
    tasks = await db.task.find_many(
        where={"menteeId": mentee_id, "date": _to_utc(session_date)},
        include={
            "problems": {"order_by": {"displayOrder": "asc"}},
            "submissions": {
                "include": {
                    "analysis": True,
                    "problemResponses": {"include": {"problem": True}},
                },
                "order_by": {"submittedAt": "desc"},
                "take": 1,
            },
            "feedbackItems": {"include": {"feedback": True}},
        },
        order={"displayOrder": "asc"},
    )

    # 이미 배정된 학습지 ID 조회 (다음날 기준)
    next_day = session_date + timedelta(days=1)
    assigned_tasks = await db.task.find_many(
        where={
            "menteeId": mentee_id,
            "date": _to_utc(next_day),
            "materialId": {"not": None},
        }
    )
    assigned_material_ids = {t.materialId for t in assigned_tasks if t.materialId}

    # 과제별 데이터 빌드
    task_items = []
    for task in tasks:
        submission = task.submissions[0] if task.submissions else None
        analysis = submission.analysis if submission else None

        # 문제별 응답 매핑
        problem_responses = []
        if submission and submission.problemResponses:
            for pr in submission.problemResponses:
                problem_responses.append({
                    "problemId": pr.problemId,
                    "problemNumber": pr.problem.number if pr.problem else 0,
                    "problemTitle": pr.problem.title if pr.problem else "",
                    "answer": pr.answer,
                    "textNote": pr.textNote,
                    "highlightData": pr.highlightData,
                    "drawingUrl": pr.drawingUrl,
                })

        submission_detail = None
        if submission:
            submission_detail = {
                "id": submission.id,
                "comment": submission.comment,
                "images": submission.images or [],
                "textContent": submission.textContent,
                "problemResponses": problem_responses,
                "selfScoreCorrect": submission.selfScoreCorrect,
                "selfScoreTotal": submission.selfScoreTotal,
                "wrongQuestions": submission.wrongQuestions or [],
                "submittedAt": submission.submittedAt,
            }

        # 분석 상세
        analysis_detail = None
        if analysis:
            analysis_detail = {
                "id": analysis.id,
                "status": analysis.status,
                "densityScore": analysis.densityScore,
                "signalLight": analysis.signalLight,
                "summary": analysis.summary,
                "detailedAnalysis": analysis.detailedAnalysis,
                "partDensity": analysis.partDensity or [],
                "traceTypes": analysis.traceTypes,
                "mentorTip": analysis.mentorTip,
            }

        # AI 피드백 초안
        ai_draft = _generate_ai_draft(analysis, task.title)

        # 추천 학습지 (과목 기반)
        materials = await db.material.find_many(
            where={"subject": task.subject},
            take=3,
            order={"createdAt": "desc"},
        )
        recommended_materials = [
            {
                "id": m.id,
                "title": m.title,
                "subject": m.subject,
                "abilityTags": m.abilityTags,
                "difficulty": m.difficulty,
                "isAssigned": m.id in assigned_material_ids,
            }
            for m in materials
        ]

        # 저장된 상세 피드백
        detail_feedback = None
        if task.feedbackItems:
            for item in task.feedbackItems:
                if item.feedback and item.feedback.mentorId == mentor_profile.id:
                    detail_feedback = item.detail
                    break

        task_items.append({
            "id": task.id,
            "title": task.title,
            "subject": task.subject,
            "abilityTag": task.abilityTag,
            "tags": task.tags or [],
            "status": task.status,
            "submission": submission_detail,
            "analysis": analysis_detail,
            "aiDraft": ai_draft,
            "recommendedMaterials": recommended_materials,
            "detailFeedback": detail_feedback,
        })

    # 학습 총평 (당일 Feedback 중 generalComment가 있는 최신 것)
    feedbacks = await db.feedback.find_many(
        where={
            "menteeId": mentee_id,
            "mentorId": mentor_profile.id,
            "date": _to_utc(session_date),
        },
        order={"createdAt": "desc"},
    )
    daily_summary = next(
        (fb.generalComment for fb in feedbacks if fb.generalComment), None
    )

    return {
        "mentee": {
            "id": mentee.id,
            "name": mentee.user.name,
            "grade": mentee.grade,
            "school": mentee.school,
        },
        "date": session_date,
        "tasks": task_items,
        "dailySummary": daily_summary,
    }


async def save_task_feedback(db: Prisma, user, data: TaskFeedbackRequest):
    """과제별 상세 피드백 저장"""
    if not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )

    task = await db.task.find_unique(where={"id": data.taskId})
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TASK_002", "message": "할 일을 찾을 수 없습니다"},
        )

    await _verify_mentor_mentee(db, user, task.menteeId)

    # 당일 Feedback 있으면 재사용, 없으면 생성
    feedback = await db.feedback.find_first(
        where={
            "menteeId": task.menteeId,
            "mentorId": user.mentorProfile.id,
            "date": task.date,
        }
    )

    if not feedback:
        feedback = await db.feedback.create(
            data={
                "mentee": {"connect": {"id": task.menteeId}},
                "mentor": {"connect": {"id": user.mentorProfile.id}},
                "date": task.date,
            }
        )

    # 기존 FeedbackItem 있으면 업데이트, 없으면 생성
    existing_item = await db.feedbackitem.find_first(
        where={"feedbackId": feedback.id, "taskId": data.taskId}
    )

    if existing_item:
        item = await db.feedbackitem.update(
            where={"id": existing_item.id},
            data={"detail": data.detail},
        )
    else:
        item = await db.feedbackitem.create(
            data={
                "feedback": {"connect": {"id": feedback.id}},
                "task": {"connect": {"id": data.taskId}},
                "detail": data.detail,
            }
        )

    return {"feedbackItemId": item.id, "taskId": data.taskId, "detail": data.detail}


async def save_daily_summary(db: Prisma, user, data: DailySummaryRequest):
    """학습 총평 저장"""
    mentor_profile = await _verify_mentor_mentee(db, user, data.menteeId)

    # 당일 Feedback 있으면 업데이트, 없으면 생성
    feedbacks = await db.feedback.find_many(
        where={
            "menteeId": data.menteeId,
            "mentorId": mentor_profile.id,
            "date": _to_utc(data.date),
        },
        order={"createdAt": "desc"},
    )
    # generalComment가 이미 있는 피드백 우선, 없으면 최신 피드백 사용
    feedback = next(
        (fb for fb in feedbacks if fb.generalComment), None
    ) or (feedbacks[0] if feedbacks else None)

    if feedback:
        feedback = await db.feedback.update(
            where={"id": feedback.id},
            data={"generalComment": data.generalComment},
        )
    else:
        feedback = await db.feedback.create(
            data={
                "mentee": {"connect": {"id": data.menteeId}},
                "mentor": {"connect": {"id": mentor_profile.id}},
                "date": _to_utc(data.date),
                "generalComment": data.generalComment,
            }
        )

    return {
        "feedbackId": feedback.id,
        "menteeId": data.menteeId,
        "date": data.date,
        "generalComment": data.generalComment,
    }
