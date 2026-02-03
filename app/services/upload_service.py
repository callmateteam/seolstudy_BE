import uuid

import boto3
from fastapi import HTTPException, UploadFile, status

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


async def _upload_to_s3(content: bytes, key: str, content_type: str) -> str:
    s3 = _get_s3()
    s3.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    return _s3_url(key)


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
