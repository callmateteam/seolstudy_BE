from fastapi import APIRouter, Depends, Response, status
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    SignupRequest,
    UserResponse,
)
from app.schemas.common import ErrorResponse, SuccessResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post(
    "/signup",
    response_model=SuccessResponse[AuthResponse],
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="아이디, 비밀번호, 이름, 휴대전화, 역할(MENTEE/MENTOR/PARENT)로 회원가입합니다. 성공 시 JWT 토큰을 발급합니다.",
    responses={
        409: {"model": ErrorResponse, "description": "이미 존재하는 아이디 (AUTH_004)"},
        422: {"description": "입력값 유효성 검증 실패"},
    },
)
async def signup(data: SignupRequest, db: Prisma = Depends(get_db)):
    result = await auth_service.signup(db, data)
    return SuccessResponse(
        data=AuthResponse(
            user=UserResponse.model_validate(result["user"]),
            accessToken=result["accessToken"],
            refreshToken=result["refreshToken"],
        ),
    )


@router.post(
    "/login",
    response_model=SuccessResponse[AuthResponse],
    summary="로그인",
    description="아이디와 비밀번호로 로그인합니다. 성공 시 JWT access/refresh 토큰을 발급합니다.",
    responses={
        401: {"model": ErrorResponse, "description": "잘못된 아이디 또는 비밀번호 (AUTH_001)"},
    },
)
async def login(data: LoginRequest, db: Prisma = Depends(get_db)):
    result = await auth_service.login(db, data.loginId, data.password)
    return SuccessResponse(
        data=AuthResponse(
            user=UserResponse.model_validate(result["user"]),
            accessToken=result["accessToken"],
            refreshToken=result["refreshToken"],
        ),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
    description="현재 세션을 로그아웃합니다. Authorization 헤더에 Bearer 토큰이 필요합니다.",
    responses={
        401: {"model": ErrorResponse, "description": "인증 실패 (AUTH_003)"},
    },
)
async def logout(current_user=Depends(get_current_user)):
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=SuccessResponse[MeResponse],
    summary="내 정보 조회",
    description="현재 로그인한 사용자의 정보와 역할별 프로필을 조회합니다. 온보딩 미완료 시 profile은 null입니다.",
    responses={
        401: {"model": ErrorResponse, "description": "인증 실패 (AUTH_003)"},
    },
)
async def me(current_user=Depends(get_current_user)):
    profile = auth_service.get_user_profile(current_user)
    return SuccessResponse(
        data=MeResponse(
            user=UserResponse.model_validate(current_user),
            profile=profile,
        ),
    )
