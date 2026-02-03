from functools import wraps
from typing import Callable

from fastapi import HTTPException, status


def require_role(*allowed_roles: str) -> Callable:
    """역할 기반 권한 체크 의존성 생성"""

    def dependency(current_user=None):
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "AUTH_003", "message": "인증이 필요합니다"},
            )
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_001", "message": "접근 권한이 없습니다"},
            )
        return current_user

    return dependency


async def check_mentee_ownership(current_user, mentee_id: str) -> None:
    """멘티가 자신의 데이터에만 접근하는지 확인"""
    if current_user.role == "MENTEE":
        if not current_user.menteeProfile or current_user.menteeProfile.id != mentee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_002", "message": "본인의 데이터만 접근 가능합니다"},
            )


async def check_mentor_access(current_user, mentee_id: str, db) -> None:
    """멘토가 담당 멘티 데이터에만 접근하는지 확인"""
    if current_user.role == "MENTOR":
        if not current_user.mentorProfile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_001", "message": "멘토 프로필이 없습니다"},
            )
        link = await db.mentormentee.find_first(
            where={
                "mentorId": current_user.mentorProfile.id,
                "menteeId": mentee_id,
            }
        )
        if link is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_002", "message": "담당 멘티의 데이터만 접근 가능합니다"},
            )


async def check_parent_access(current_user, mentee_id: str) -> None:
    """학부모가 자녀 데이터에만 접근하는지 확인"""
    if current_user.role == "PARENT":
        if not current_user.parentProfile or current_user.parentProfile.menteeId != mentee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "PERM_002", "message": "자녀의 데이터만 접근 가능합니다"},
            )
