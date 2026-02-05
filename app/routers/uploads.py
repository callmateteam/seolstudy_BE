from fastapi import APIRouter, Depends, UploadFile

from app.core.deps import get_current_user
from app.schemas.common import ErrorResponse, SuccessResponse
from app.schemas.upload import (
    ImageValidationResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
    StudyPhotoResponse,
    UploadResponse,
)
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
    "/study-photo",
    response_model=SuccessResponse[StudyPhotoResponse],
    status_code=201,
    summary="학습 인증 사진 업로드",
    description="학습 인증 사진을 업로드하고 OCR 가독성을 검증합니다. "
    "ocrReady=false인 경우 사진이 선명하지 않으나, 그대로 제출하거나 다시 업로드할 수 있습니다.",
    responses={
        400: {"model": ErrorResponse, "description": "파일 형식/크기 오류"},
    },
)
async def upload_study_photo(
    file: UploadFile,
    current_user=Depends(get_current_user),
):
    result = await upload_service.upload_study_photo(file)
    return SuccessResponse(data=StudyPhotoResponse(**result))


@router.post(
    "/presigned-url",
    response_model=SuccessResponse[PresignedUrlResponse],
    summary="Presigned URL 생성",
    description="S3 URL에 대한 presigned GET URL을 생성합니다. 프론트엔드에서 이미지 표시용.",
)
async def get_presigned_url(
    data: PresignedUrlRequest,
    current_user=Depends(get_current_user),
):
    result = upload_service.generate_presigned_url_from_s3_url(data.url)
    return SuccessResponse(data=PresignedUrlResponse(**result))


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
