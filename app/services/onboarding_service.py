from fastapi import HTTPException, status
from prisma import Json, Prisma

from app.schemas.onboarding import (
    MenteeOnboardingRequest,
    MentorOnboardingRequest,
    ParentOnboardingRequest,
)

VALID_SUBJECTS = {"KOREAN", "ENGLISH", "MATH"}


def _validate_subjects(subjects: list[str]) -> None:
    invalid = set(subjects) - VALID_SUBJECTS
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "ONBOARD_001",
                "message": f"잘못된 과목: {', '.join(invalid)}. 허용: KOREAN, ENGLISH, MATH",
            },
        )


def _validate_grade_scores(grades: dict[str, int], subjects: list[str]) -> None:
    for subj in subjects:
        score = grades.get(subj)
        if score is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ONBOARD_002",
                    "message": f"과목 {subj}의 등급이 누락되었습니다",
                },
            )
        if not 1 <= score <= 9:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ONBOARD_002",
                    "message": f"등급은 1~9 범위여야 합니다 ({subj}: {score})",
                },
            )


async def onboard_mentee(db: Prisma, user, data: MenteeOnboardingRequest):
    if user.role != "MENTEE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘티만 접근 가능합니다"},
        )

    existing = await db.menteeprofile.find_unique(where={"userId": user.id})
    if existing and existing.onboardingDone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ONBOARD_003", "message": "이미 온보딩이 완료되었습니다"},
        )

    _validate_subjects(data.subjects)
    _validate_grade_scores(data.currentGrades, data.subjects)
    _validate_grade_scores(data.targetGrades, data.subjects)

    if existing:
        profile = await db.menteeprofile.update(
            where={"userId": user.id},
            data={
                "school": data.school,
                "grade": data.grade,
                "subjects": data.subjects,
                "currentGrades": Json(data.currentGrades),
                "targetGrades": Json(data.targetGrades),
                "onboardingDone": True,
            },
        )
    else:
        profile = await db.menteeprofile.create(
            data={
                "user": {"connect": {"id": user.id}},
                "school": data.school,
                "grade": data.grade,
                "subjects": data.subjects,
                "currentGrades": Json(data.currentGrades),
                "targetGrades": Json(data.targetGrades),
                "onboardingDone": True,
            }
        )

    return profile


async def onboard_mentor(db: Prisma, user, data: MentorOnboardingRequest):
    if user.role != "MENTOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토만 접근 가능합니다"},
        )

    existing = await db.mentorprofile.find_unique(where={"userId": user.id})
    if existing and existing.onboardingDone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ONBOARD_003", "message": "이미 온보딩이 완료되었습니다"},
        )

    _validate_subjects(data.subjects)

    if existing:
        profile = await db.mentorprofile.update(
            where={"userId": user.id},
            data={
                "university": data.university,
                "department": data.department,
                "subjects": data.subjects,
                "coachingExperience": data.coachingExperience,
                "onboardingDone": True,
            },
        )
    else:
        profile = await db.mentorprofile.create(
            data={
                "user": {"connect": {"id": user.id}},
                "university": data.university,
                "department": data.department,
                "subjects": data.subjects,
                "coachingExperience": data.coachingExperience,
                "onboardingDone": True,
            }
        )

    if data.menteeInviteCode:
        mentee = await db.menteeprofile.find_unique(
            where={"inviteCode": data.menteeInviteCode}
        )
        if mentee:
            existing_link = await db.mentormentee.find_first(
                where={"mentorId": profile.id, "menteeId": mentee.id}
            )
            if not existing_link:
                await db.mentormentee.create(
                    data={
                        "mentor": {"connect": {"id": profile.id}},
                        "mentee": {"connect": {"id": mentee.id}},
                    }
                )

    return profile


async def onboard_parent(db: Prisma, user, data: ParentOnboardingRequest):
    if user.role != "PARENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "학부모만 접근 가능합니다"},
        )

    existing = await db.parentprofile.find_unique(where={"userId": user.id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ONBOARD_003", "message": "이미 온보딩이 완료되었습니다"},
        )

    mentee = await db.menteeprofile.find_unique(
        where={"inviteCode": data.inviteCode}
    )
    if not mentee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ONBOARD_004", "message": "유효하지 않은 초대 코드입니다"},
        )

    profile = await db.parentprofile.create(
        data={
            "user": {"connect": {"id": user.id}},
            "mentee": {"connect": {"id": mentee.id}},
        }
    )

    return profile
