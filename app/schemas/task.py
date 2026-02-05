import datetime as dt
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ===== Problem schemas =====

class TaskProblemCreateRequest(BaseModel):
    number: int = Field(ge=1, examples=[1])
    title: str = Field(min_length=1, max_length=500, examples=["다음 글을 읽고 물음에 답하시오."])
    content: str | None = Field(default=None, max_length=5000)
    options: list[dict] | None = Field(
        default=None,
        examples=[[{"label": "1", "text": "선지 내용"}]],
    )
    correctAnswer: str | None = Field(default=None, max_length=200)
    displayOrder: int = Field(default=0, ge=0)


class TaskProblemUpdateRequest(BaseModel):
    number: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None
    options: list[dict] | None = None
    correctAnswer: str | None = None
    displayOrder: int | None = Field(default=None, ge=0)


class TaskProblemResponse(BaseModel):
    id: str
    taskId: str
    number: int
    title: str
    content: str | None = None
    options: Any | None = None
    displayOrder: int

    model_config = {"from_attributes": True}


class TaskProblemWithAnswerResponse(TaskProblemResponse):
    """멘토용 — correctAnswer 포함."""
    correctAnswer: str | None = None


# ===== Task schemas =====

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
    repeat: bool = Field(default=False, description="반복 여부")
    repeatDays: list[str] | None = Field(
        default=None,
        description="반복 요일 (MON,TUE,WED,THU,FRI,SAT,SUN)",
        examples=[["MON", "WED", "FRI"]],
    )
    targetStudyMinutes: int | None = Field(
        default=None, ge=0, le=1440,
        description="목표 공부 시간(분)",
        examples=[90],
    )
    memo: str | None = Field(default=None, max_length=1000, examples=["풀이 과정에 집중하기"])
    tags: list[str] = Field(default=[], examples=[["국어", "문해력", "비문학"]])
    keyPoints: str | None = Field(default=None, max_length=5000)
    content: str | None = Field(default=None, max_length=10000)
    problems: list[TaskProblemCreateRequest] | None = Field(
        default=None, description="문제 목록 (멘토 전용)",
    )
    displayOrder: int = Field(default=0, ge=0)


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    goal: str | None = None
    subject: str | None = Field(default=None, pattern="^(KOREAN|ENGLISH|MATH)$")
    abilityTag: str | None = None
    materialType: str | None = Field(default=None, pattern="^(COLUMN|PDF)$")
    materialId: str | None = None
    materialUrl: str | None = None
    repeat: bool | None = None
    repeatDays: list[str] | None = None
    targetStudyMinutes: int | None = Field(default=None, ge=0, le=1440)
    memo: str | None = None
    tags: list[str] | None = None
    keyPoints: str | None = None
    content: str | None = None
    displayOrder: int | None = Field(default=None, ge=0)


class StudyTimeRequest(BaseModel):
    minutes: int = Field(ge=0, le=1440, examples=[45], description="공부 시간(분)")


class BookmarkRequest(BaseModel):
    isBookmarked: bool


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
    repeat: bool = False
    repeatDays: list[str] = []
    targetStudyMinutes: int | None = None
    memo: str | None = None
    tags: list[str] = []
    keyPoints: str | None = None
    content: str | None = None
    isBookmarked: bool = False
    problems: list[TaskProblemResponse] = []
    problemCount: int = 0
    createdBy: str
    displayOrder: int

    @field_validator("problems", mode="before")
    @classmethod
    def _coerce_problems(cls, v):
        return v if v is not None else []

    model_config = {"from_attributes": True}
