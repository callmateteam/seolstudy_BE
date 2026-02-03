from datetime import datetime, timezone

from fastapi import HTTPException, status
from prisma import Prisma

from app.schemas.coaching import AssignMaterialRequest


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
