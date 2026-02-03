import os
import uuid

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


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

    _ensure_upload_dir()
    saved_name = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(UPLOAD_DIR, saved_name)
    with open(path, "wb") as f:
        f.write(content)

    return {
        "url": f"/uploads/{saved_name}",
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

    _ensure_upload_dir()
    saved_name = f"{uuid.uuid4()}.{ext}"
    path = os.path.join(UPLOAD_DIR, saved_name)
    with open(path, "wb") as f:
        f.write(content)

    return {
        "url": f"/uploads/{saved_name}",
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
