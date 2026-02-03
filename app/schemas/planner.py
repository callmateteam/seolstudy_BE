import datetime as dt

from pydantic import BaseModel, Field

from app.schemas.task import TaskResponse


class CommentCreateRequest(BaseModel):
    date: dt.date = Field(examples=["2026-02-03"])
    content: str = Field(min_length=1, max_length=1000, examples=["오늘 수학 어려웠어요"])


class CommentResponse(BaseModel):
    id: str
    menteeId: str
    date: dt.date
    content: str
    createdAt: dt.datetime

    model_config = {"from_attributes": True}


class PlannerResponse(BaseModel):
    date: dt.date
    tasks: list[TaskResponse]
    comments: list[CommentResponse]
    completionRate: float = Field(description="완수율 (0.0 ~ 1.0)")


class CompletionRateResponse(BaseModel):
    date: dt.date
    total: int
    completed: int
    rate: float


class WeeklyDayStatus(BaseModel):
    date: dt.date
    total: int
    completed: int
    rate: float


class WeeklyResponse(BaseModel):
    weekOf: dt.date
    days: list[WeeklyDayStatus]
