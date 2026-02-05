from fastapi import APIRouter, Depends

from app.core.deps import db, get_current_user
from app.schemas.common import SuccessResponse
from app.schemas.my import MyPageResponse, MyPageUpdateRequest
from app.services import my_service

router = APIRouter(prefix="/api/my", tags=["My Page"])


@router.get("", response_model=SuccessResponse[MyPageResponse])
async def get_my_page(current_user=Depends(get_current_user)):
    """
    마이 페이지 정보를 조회합니다.

    - 역할(멘티/멘토/학부모)에 따라 다른 정보 반환
    - 멘티: 학교, 학년, 과목, 담당 멘토, 과목별 달성률, 활동 요약
    - 멘토: 과목
    - 학부모: 기본 정보만
    """
    result = await my_service.get_my_page(db, current_user)
    return SuccessResponse(data=result)


@router.patch("", response_model=SuccessResponse[MyPageResponse])
async def update_my_page(
    data: MyPageUpdateRequest,
    current_user=Depends(get_current_user),
):
    """
    마이 페이지 정보를 수정합니다.

    - 이름: 모든 역할 수정 가능
    - 학교: 멘티만 수정 가능
    """
    result = await my_service.update_my_page(db, current_user, data)
    return SuccessResponse(data=result)
