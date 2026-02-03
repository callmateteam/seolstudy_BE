from fastapi import APIRouter, Depends, UploadFile

from app.core.deps import get_current_user
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.upload import ImageValidationResponse, UploadResponse
from app.services import upload_service

router = APIRouter(prefix="/api/uploads", tags=["Uploads"])


@router.post(
    "/image",
    response_model=SuccessResponse[UploadResponse],
    status_code=201,
    summary="이미지 업로드",
    description="JPG/PNG 이미지를 업로드합니다. 최대 5MB.",
    responses={
        400: {"model": ErrorResponse, "description": "파일 형식/크기 오류"},
    },
)
async def upload_image(
    file: UploadFile,
    current_user=Depends(get_current_user),
):
    result = await upload_service.upload_image(file)
    return SuccessResponse(data=UploadResponse(**result))


@router.post(
    "/pdf",
    response_model=SuccessResponse[UploadResponse],
    status_code=201,
    summary="PDF 업로드",
    description="PDF 파일을 업로드합니다. 최대 20MB. 멘토만 가능합니다.",
    responses={
        400: {"model": ErrorResponse, "description": "파일 형식/크기 오류"},
    },
)
async def upload_pdf(
    file: UploadFile,
    current_user=Depends(get_current_user),
):
    result = await upload_service.upload_pdf(file)
    return SuccessResponse(data=UploadResponse(**result))


@router.post(
    "/validate-image",
    response_model=SuccessResponse[ImageValidationResponse],
    summary="이미지 품질 검증",
    description="업로드 전 이미지 품질(해상도, 크기)을 검증합니다.",
)
async def validate_image(
    file: UploadFile,
    current_user=Depends(get_current_user),
):
    result = await upload_service.validate_image(file)
    return SuccessResponse(data=ImageValidationResponse(**result))
