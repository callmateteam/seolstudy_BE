from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from prisma import Prisma

from app.core.deps import get_current_user, get_db
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.material import MaterialCreateRequest, MaterialResponse
from app.services import material_service

router = APIRouter(prefix="/api/materials", tags=["Materials"])


@router.get(
    "",
    response_model=SuccessResponse[list[MaterialResponse]],
    summary="학습지 목록",
    description="과목, 유형별로 학습지를 조회합니다.",
)
async def get_materials(
    subject: str | None = None,
    type: str | None = None,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    materials = await material_service.get_materials(db, subject, type)
    return SuccessResponse(
        data=[MaterialResponse.model_validate(m) for m in materials]
    )


@router.get(
    "/{materialId}",
    response_model=SuccessResponse[MaterialResponse],
    summary="학습지 상세",
    description="특정 학습지의 상세 정보를 조회합니다.",
    responses={
        404: {"model": ErrorResponse, "description": "학습지 없음 (MATERIAL_001)"},
    },
)
async def get_material(
    materialId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    material = await material_service.get_material(db, materialId)
    return SuccessResponse(data=MaterialResponse.model_validate(material))


@router.post(
    "",
    response_model=SuccessResponse[MaterialResponse],
    status_code=201,
    summary="학습지 등록",
    description="새로운 학습지를 등록합니다. 멘토만 가능합니다.",
)
async def create_material(
    data: MaterialCreateRequest,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    material = await material_service.create_material(db, data)
    return SuccessResponse(data=MaterialResponse.model_validate(material))


@router.get(
    "/{materialId}/download",
    summary="학습지 다운로드",
    description="학습지 파일(PDF/칼럼)의 URL로 리다이렉트합니다.",
    responses={
        404: {"model": ErrorResponse, "description": "학습지 없음 (MATERIAL_001)"},
    },
)
async def download_material(
    materialId: str,
    current_user=Depends(get_current_user),
    db: Prisma = Depends(get_db),
):
    material = await material_service.get_material(db, materialId)
    return RedirectResponse(url=material.contentUrl)
