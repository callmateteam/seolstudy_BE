from fastapi import HTTPException, status
from prisma import Prisma

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import SignupRequest


async def signup(db: Prisma, data: SignupRequest) -> dict:
    existing = await db.user.find_unique(where={"loginId": data.loginId})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "AUTH_004", "message": "이미 존재하는 아이디입니다"},
        )

    user = await db.user.create(
        data={
            "loginId": data.loginId,
            "passwordHash": hash_password(data.password),
            "role": data.role,
            "name": data.name,
            "phone": data.phone,
        }
    )

    access_token = create_access_token(subject=user.id, role=user.role)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "user": user,
        "accessToken": access_token,
        "refreshToken": refresh_token,
    }


async def login(db: Prisma, login_id: str, password: str) -> dict:
    user = await db.user.find_unique(where={"loginId": login_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_001", "message": "잘못된 아이디 또는 비밀번호입니다"},
        )

    if not verify_password(password, user.passwordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_001", "message": "잘못된 아이디 또는 비밀번호입니다"},
        )

    access_token = create_access_token(subject=user.id, role=user.role)
    refresh_token = create_refresh_token(subject=user.id)

    return {
        "user": user,
        "accessToken": access_token,
        "refreshToken": refresh_token,
    }


def get_user_profile(user) -> dict | None:
    if user.role == "MENTEE" and user.menteeProfile:
        p = user.menteeProfile
        return {
            "id": p.id,
            "grade": p.grade,
            "subjects": p.subjects,
            "currentGrades": p.currentGrades,
            "targetGrades": p.targetGrades,
            "onboardingDone": p.onboardingDone,
            "inviteCode": p.inviteCode,
        }
    elif user.role == "MENTOR" and user.mentorProfile:
        p = user.mentorProfile
        return {
            "id": p.id,
            "university": p.university,
            "department": p.department,
            "subjects": p.subjects,
            "coachingExperience": p.coachingExperience,
            "onboardingDone": p.onboardingDone,
        }
    elif user.role == "PARENT" and user.parentProfile:
        p = user.parentProfile
        return {
            "id": p.id,
            "menteeId": p.menteeId,
        }
    return None
