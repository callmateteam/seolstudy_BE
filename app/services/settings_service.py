from fastapi import HTTPException, status
from prisma import Json, Prisma

from app.schemas.settings import MenteeSettingsRequest, MentorSettingsRequest, ProfileUpdateRequest


async def get_profile(user):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "profileImage": user.profileImage,
        "nickname": user.nickname,
        "role": user.role,
    }


async def update_profile(db: Prisma, user, data: ProfileUpdateRequest):
    update_data: dict = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.phone is not None:
        update_data["phone"] = data.phone
    if data.nickname is not None:
        update_data["nickname"] = data.nickname
    if data.profileImage is not None:
        update_data["profileImage"] = data.profileImage

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SETTINGS_001", "message": "수정할 내용이 없습니다"},
        )

    updated = await db.user.update(
        where={"id": user.id},
        data=update_data,
    )
    return {
        "id": updated.id,
        "email": updated.email,
        "name": updated.name,
        "phone": updated.phone,
        "profileImage": updated.profileImage,
        "nickname": updated.nickname,
        "role": updated.role,
    }


async def update_mentee_settings(db: Prisma, user, data: MenteeSettingsRequest):
    if not user.menteeProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘티 권한이 필요합니다"},
        )

    update_data: dict = {}
    if data.targetGrades is not None:
        update_data["targetGrades"] = Json(data.targetGrades)
    if data.subjects is not None:
        update_data["subjects"] = data.subjects

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SETTINGS_001", "message": "수정할 내용이 없습니다"},
        )

    await db.menteeprofile.update(
        where={"id": user.menteeProfile.id},
        data=update_data,
    )
    return {"message": "멘티 설정이 업데이트되었습니다"}


async def update_mentor_settings(db: Prisma, user, data: MentorSettingsRequest):
    if not user.mentorProfile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERM_001", "message": "멘토 권한이 필요합니다"},
        )

    update_data: dict = {}
    if data.subjects is not None:
        update_data["subjects"] = data.subjects

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SETTINGS_001", "message": "수정할 내용이 없습니다"},
        )

    await db.mentorprofile.update(
        where={"id": user.mentorProfile.id},
        data=update_data,
    )
    return {"message": "멘토 설정이 업데이트되었습니다"}
