import io
import uuid

import boto3
from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.core.config import settings

_s3_client = None


def _get_s3():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
    return _s3_client


def _get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _s3_url(key: str) -> str:
    return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


def _key_from_url(url: str) -> str:
    """S3 URL에서 key를 추출합니다."""
    prefix = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/"
    if url.startswith(prefix):
        return url[len(prefix):]
    return url


def _is_mock_mode() -> bool:
    """CI/테스트 환경에서는 S3 업로드를 mock합니다."""
    return settings.AWS_ACCESS_KEY_ID == "test" or settings.APP_ENV == "test"


def generate_presigned_url(key: str) -> str:
    if _is_mock_mode():
        return f"{_s3_url(key)}?mock-presigned=true"

    s3 = _get_s3()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=settings.PRESIGNED_URL_EXPIRE_SECONDS,
    )


def generate_presigned_url_from_s3_url(s3_url: str) -> dict:
    key = _key_from_url(s3_url)
    presigned = generate_presigned_url(key)
    return {
        "presignedUrl": presigned,
        "expiresIn": settings.PRESIGNED_URL_EXPIRE_SECONDS,
    }


async def _upload_to_s3(content: bytes, key: str, content_type: str) -> str:
    if _is_mock_mode():
        return _s3_url(key)

    s3 = _get_s3()
    s3.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    return _s3_url(key)


def _check_image_clarity(content: bytes) -> dict:
    """이미지 OCR 가독성을 검증합니다."""
    try:
        img = Image.open(io.BytesIO(content))
        width, height = img.size

        if width < 640 or height < 480:
            return {
                "ocrReady": False,
                "ocrMessage": "사진이 선명하지 않아 인증이 어려워요. 해상도가 너무 낮습니다.",
            }

        if img.mode in ("L", "LA"):
            gray = img
        else:
            gray = img.convert("L")

        pixels = list(gray.getdata())
        n = len(pixels)
        mean = sum(pixels) / n
        variance = sum((p - mean) ** 2 for p in pixels) / n

        if variance < 200:
            return {
                "ocrReady": False,
                "ocrMessage": "사진이 선명하지 않아 인증이 어려워요. 명암 대비가 부족합니다.",
            }

        return {
            "ocrReady": True,
            "ocrMessage": "사진이 선명하게 촬영되었습니다.",
        }
    except Exception:
        return {
            "ocrReady": False,
            "ocrMessage": "이미지를 분석할 수 없습니다. 다시 업로드해주세요.",
        }


async def upload_image(file: UploadFile) -> dict:
    ext = _get_extension(file.filename or "")
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_002", "message": f"지원하지 않는 파일 형식입니다. 허용: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"},
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_IMAGE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_003", "message": f"파일 크기가 {settings.MAX_IMAGE_SIZE_MB}MB를 초과합니다"},
        )

    key = f"images/{uuid.uuid4()}.{ext}"
    content_type = file.content_type or f"image/{ext}"
    url = await _upload_to_s3(content, key, content_type)

    return {
        "url": url,
        "originalName": file.filename or "",
        "size": len(content),
    }


async def upload_pdf(file: UploadFile) -> dict:
    ext = _get_extension(file.filename or "")
    if ext not in settings.ALLOWED_PDF_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_002", "message": "PDF 파일만 업로드 가능합니다"},
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_PDF_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_003", "message": f"파일 크기가 {settings.MAX_PDF_SIZE_MB}MB를 초과합니다"},
        )

    key = f"pdfs/{uuid.uuid4()}.{ext}"
    url = await _upload_to_s3(content, key, "application/pdf")

    return {
        "url": url,
        "originalName": file.filename or "",
        "size": len(content),
        "rawBytes": content,
    }


async def upload_study_photo(file: UploadFile) -> dict:
    """학습 인증 사진 업로드 + OCR 가독성 검증."""
    ext = _get_extension(file.filename or "")
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_002", "message": f"지원하지 않는 파일 형식입니다. 허용: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"},
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_IMAGE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUBMIT_003", "message": f"파일 크기가 {settings.MAX_IMAGE_SIZE_MB}MB를 초과합니다"},
        )

    key = f"study-photos/{uuid.uuid4()}.{ext}"
    content_type = file.content_type or f"image/{ext}"
    url = await _upload_to_s3(content, key, content_type)

    ocr_result = _check_image_clarity(content)
    presigned = generate_presigned_url(key)

    return {
        "url": url,
        "presignedUrl": presigned,
        "originalName": file.filename or "",
        "size": len(content),
        **ocr_result,
    }


async def validate_image(file: UploadFile) -> dict:
    ext = _get_extension(file.filename or "")
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        return {"valid": False, "issues": ["지원하지 않는 파일 형식입니다"]}

    content = await file.read()
    issues: list[str] = []

    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_IMAGE_SIZE_MB:
        issues.append(f"파일 크기가 {settings.MAX_IMAGE_SIZE_MB}MB를 초과합니다")

    if len(content) < 10_000:
        issues.append("이미지 해상도가 너무 낮을 수 있습니다")

    return {"valid": len(issues) == 0, "issues": issues}
