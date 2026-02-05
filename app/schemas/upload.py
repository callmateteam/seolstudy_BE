from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    url: str
    originalName: str
    size: int


class ImageValidationResponse(BaseModel):
    valid: bool
    issues: list[str] = []


class StudyPhotoResponse(BaseModel):
    url: str
    presignedUrl: str
    originalName: str
    size: int
    ocrReady: bool
    ocrMessage: str


class PresignedUrlRequest(BaseModel):
    url: str = Field(description="S3 URL")


class PresignedUrlResponse(BaseModel):
    presignedUrl: str
    expiresIn: int
