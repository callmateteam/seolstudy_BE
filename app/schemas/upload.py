from pydantic import BaseModel


class UploadResponse(BaseModel):
    url: str
    originalName: str
    size: int


class ImageValidationResponse(BaseModel):
    valid: bool
    issues: list[str] = []
