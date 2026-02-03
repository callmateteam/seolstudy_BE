import datetime as dt

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    date: dt.date = Field(examples=["2026-02-03"])
    title: str = Field(min_length=1, max_length=200, examples=["수학 미적분 p.32~35"])
    goal: str | None = Field(default=None, max_length=500, examples=["미분 개념 정리"])
    subject: str = Field(pattern="^(KOREAN|ENGLISH|MATH)$", examples=["MATH"])
    abilityTag: str | None = Field(default=None, max_length=50, examples=["미적분"])
    materialType: str | None = Field(
        default=None, pattern="^(COLUMN|PDF)$", examples=["PDF"]
    )
    materialId: str | None = None
    materialUrl: str | None = None
    displayOrder: int = Field(default=0, ge=0)


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    goal: str | None = None
    subject: str | None = Field(default=None, pattern="^(KOREAN|ENGLISH|MATH)$")
    abilityTag: str | None = None
    materialType: str | None = Field(default=None, pattern="^(COLUMN|PDF)$")
    materialId: str | None = None
    materialUrl: str | None = None
    displayOrder: int | None = Field(default=None, ge=0)


class StudyTimeRequest(BaseModel):
    minutes: int = Field(ge=0, le=1440, examples=[45], description="공부 시간(분)")


class TaskResponse(BaseModel):
    id: str
    menteeId: str
    createdByMentorId: str | None = None
    date: dt.date
    title: str
    goal: str | None = None
    subject: str
    abilityTag: str | None = None
    materialType: str | None = None
    materialId: str | None = None
    materialUrl: str | None = None
    isLocked: bool
    status: str
    studyTimeMinutes: int | None = None
    createdBy: str
    displayOrder: int

    model_config = {"from_attributes": True}
