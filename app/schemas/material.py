from datetime import datetime

from pydantic import BaseModel, Field


class MaterialCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["수능 국어 문해력 기본"])
    type: str = Field(pattern="^(COLUMN|PDF)$", examples=["PDF"])
    subject: str = Field(pattern="^(KOREAN|ENGLISH|MATH)$", examples=["KOREAN"])
    abilityTags: list[str] = Field(default=[], examples=[["문해력", "논리력"]])
    difficulty: int | None = Field(default=None, ge=1, le=5, examples=[3])
    contentUrl: str = Field(examples=["https://example.com/material.pdf"])


class MaterialResponse(BaseModel):
    id: str
    title: str
    type: str
    subject: str
    abilityTags: list[str]
    difficulty: int | None = None
    contentUrl: str
    createdAt: datetime

    model_config = {"from_attributes": True}
