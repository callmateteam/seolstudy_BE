from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from prisma import Prisma

security_scheme = HTTPBearer()

db = Prisma()


async def get_db() -> Prisma:
    return db


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    database: Prisma = Depends(get_db),
):
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_003", "message": "유효하지 않은 토큰입니다"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_003", "message": "유효하지 않은 토큰입니다"},
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_003", "message": "유효하지 않은 토큰입니다"},
        )

    user = await database.user.find_unique(
        where={"id": user_id},
        include={
            "menteeProfile": True,
            "mentorProfile": True,
            "parentProfile": True,
        },
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_001", "message": "사용자를 찾을 수 없습니다"},
        )

    return user
