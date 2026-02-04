import datetime as dt

from pydantic import BaseModel, Field

from app.schemas.task import TaskResponse


class CommentCreateRequest(BaseModel):
    date: dt.date = Field(examples=["2026-02-03"])
    content: str = Field(min_length=1, max_length=1000, examples=["오늘 수학 어려웠어요"])


class CommentReplyRequest(BaseModel):
    reply: str = Field(min_length=1, max_length=1000, examples=["수학 풀이 과정을 다시 확인해보세요"])


class CommentResponse(BaseModel):
    id: str
    menteeId: str
    date: dt.date
    content: str
    mentorReply: str | None = None
    repliedAt: dt.datetime | None = None
    createdAt: dt.datetime

    model_config = {"from_attributes": True}


class TodayFeedbackResponse(BaseModel):
    id: str
    date: dt.date
    summary: str | None = None
    generalComment: str | None = None
    isHighlighted: bool = False
    mentorName: str | None = None


class PlannerResponse(BaseModel):
    date: dt.date
    tasks: list[TaskResponse]
    comments: list[CommentResponse]
    completionRate: float = Field(description="완수율 (0.0 ~ 1.0)")
    totalCount: int = Field(description="전체 할 일 수")
    completedCount: int = Field(description="완료된 할 일 수")
    hasYesterdayFeedback: bool = Field(description="어제 피드백 존재 여부")
    yesterdayFeedbackDate: dt.date | None = Field(default=None, description="어제 날짜")
    todayFeedback: TodayFeedbackResponse | None = Field(default=None, description="오늘 종합 피드백")


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


class MonthlyDayStatus(BaseModel):
    date: dt.date
    total: int
    completed: int
    rate: float


class MonthlyResponse(BaseModel):
    year: int
    month: int
    days: list[MonthlyDayStatus]
