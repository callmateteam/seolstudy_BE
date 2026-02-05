from fastapi import HTTPException, status
from prisma import Prisma
from prisma.models import User

from app.schemas.my import (
    ActivitySummary,
    MentorInfo,
    MyPageResponse,
    MyPageUpdateRequest,
    SubjectStat,
)


async def get_my_page(db: Prisma, user: User) -> MyPageResponse:
    """마이 페이지 정보를 조회합니다."""

    base_response = {
        "id": user.id,
        "role": user.role,
        "name": user.name,
        "profileImage": user.profileImage,
        "joinedAt": user.createdAt,
    }

    if user.role == "MENTEE":
        return await _get_mentee_my_page(db, user, base_response)
    elif user.role == "MENTOR":
        return await _get_mentor_my_page(db, user, base_response)
    elif user.role == "PARENT":
        return await _get_parent_my_page(db, user, base_response)

    return MyPageResponse(**base_response)


async def _get_mentee_my_page(
    db: Prisma, user: User, base: dict
) -> MyPageResponse:
    """멘티 마이 페이지"""

    mentee = await db.menteeprofile.find_unique(
        where={"userId": user.id},
        include={
            "mentors": {
                "include": {
                    "mentor": {
                        "include": {"user": True}
                    }
                }
            }
        }
    )

    if not mentee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MY_001", "message": "멘티 프로필을 찾을 수 없습니다"},
        )

    # 멘토 정보
    mentor_info = None
    if mentee.mentors and len(mentee.mentors) > 0:
        mentor_rel = mentee.mentors[0]
        mentor = mentor_rel.mentor
        mentor_info = MentorInfo(
            id=mentor.id,
            name=mentor.user.name,
            university=mentor.university,
            department=mentor.department,
        )

    # 과목별 통계 계산
    subject_stats = await _calculate_subject_stats(db, mentee.id, mentee.subjects)

    # 활동 요약 계산
    activity_summary = await _calculate_activity_summary(db, mentee.id)

    return MyPageResponse(
        **base,
        school=mentee.school,
        grade=mentee.grade,
        subjects=mentee.subjects,
        mentor=mentor_info,
        subjectStats=subject_stats,
        activitySummary=activity_summary,
    )


async def _get_mentor_my_page(
    db: Prisma, user: User, base: dict
) -> MyPageResponse:
    """멘토 마이 페이지"""

    mentor = await db.mentorprofile.find_unique(where={"userId": user.id})

    if not mentor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MY_001", "message": "멘토 프로필을 찾을 수 없습니다"},
        )

    return MyPageResponse(
        **base,
        subjects=mentor.subjects,
    )


async def _get_parent_my_page(
    db: Prisma, user: User, base: dict
) -> MyPageResponse:
    """학부모 마이 페이지"""

    parent = await db.parentprofile.find_unique(
        where={"userId": user.id},
        include={"mentee": {"include": {"user": True}}},
    )

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MY_001", "message": "학부모 프로필을 찾을 수 없습니다"},
        )

    return MyPageResponse(**base)


async def _calculate_subject_stats(
    db: Prisma, mentee_id: str, subjects: list[str]
) -> list[SubjectStat]:
    """과목별 통계를 계산합니다."""

    stats = []

    for subject in subjects:
        # 해당 과목의 과제들 조회
        tasks = await db.task.find_many(
            where={"menteeId": mentee_id, "subject": subject},
            include={
                "submissions": {
                    "include": {"analysis": True},
                    "order_by": {"submittedAt": "desc"},
                    "take": 1,
                }
            },
        )

        total_tasks = len(tasks)
        completed_tasks = sum(
            1 for t in tasks if t.status in ("SUBMITTED", "COMPLETED")
        )
        completion_rate = (
            round((completed_tasks / total_tasks) * 100, 1)
            if total_tasks > 0
            else 0.0
        )

        # 능력 태그 수집 (중복 제거)
        ability_tags = set()
        for task in tasks:
            if task.abilityTag:
                ability_tags.add(task.abilityTag)
            if task.tags:
                ability_tags.update(task.tags)

        # 평균 밀도 점수 계산
        density_scores = []
        for task in tasks:
            if task.submissions:
                submission = task.submissions[0]
                if submission.analysis and submission.analysis.densityScore:
                    density_scores.append(submission.analysis.densityScore)

        avg_density = (
            round(sum(density_scores) / len(density_scores), 1)
            if density_scores
            else None
        )

        stats.append(
            SubjectStat(
                subject=subject,
                abilityTags=sorted(ability_tags),
                totalTasks=total_tasks,
                completedTasks=completed_tasks,
                completionRate=completion_rate,
                avgDensityScore=avg_density,
            )
        )

    return stats


async def _calculate_activity_summary(
    db: Prisma, mentee_id: str
) -> ActivitySummary:
    """활동 요약을 계산합니다."""

    # 전체 과제 조회
    tasks = await db.task.find_many(where={"menteeId": mentee_id})

    total_tasks = len(tasks)
    completed_tasks = sum(
        1 for t in tasks if t.status in ("SUBMITTED", "COMPLETED")
    )
    completion_rate = (
        round((completed_tasks / total_tasks) * 100, 1)
        if total_tasks > 0
        else 0.0
    )

    # 활동 일수 계산 (과제가 있는 날짜 수)
    active_dates = set()
    for task in tasks:
        if task.status in ("SUBMITTED", "COMPLETED"):
            active_dates.add(task.date)

    return ActivitySummary(
        activeDays=len(active_dates),
        totalCompletedTasks=completed_tasks,
        overallCompletionRate=completion_rate,
    )


async def update_my_page(
    db: Prisma, user: User, data: MyPageUpdateRequest
) -> MyPageResponse:
    """마이 페이지 정보를 수정합니다. (이름, 학교만 가능)"""

    update_data = {}

    # 이름 수정
    if data.name is not None:
        await db.user.update(
            where={"id": user.id},
            data={"name": data.name},
        )

    # 학교 수정 (멘티만)
    if data.school is not None and user.role == "MENTEE":
        await db.menteeprofile.update(
            where={"userId": user.id},
            data={"school": data.school},
        )

    # 수정된 정보 다시 조회
    updated_user = await db.user.find_unique(where={"id": user.id})
    return await get_my_page(db, updated_user)
