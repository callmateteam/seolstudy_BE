from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from prisma import Prisma

security_scheme = HTTPBearer(auto_error=False)

db = Prisma()

COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


async def get_db() -> Prisma:
    return db


def _get_token_from_request(
    credentials: Optional[HTTPAuthorizationCredentials],
    access_token_cookie: Optional[str],
) -> str:
    """쿠키 또는 Authorization 헤더에서 토큰을 추출합니다."""
    # 1. Authorization 헤더 우선
    if credentials and credentials.credentials:
        return credentials.credentials

    # 2. 쿠키에서 토큰 추출
    if access_token_cookie:
        return access_token_cookie

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "AUTH_003", "message": "인증 토큰이 필요합니다"},
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    access_token: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
    database: Prisma = Depends(get_db),
):
    token = _get_token_from_request(credentials, access_token)
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
