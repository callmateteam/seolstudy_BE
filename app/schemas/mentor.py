import datetime as dt

from pydantic import BaseModel, Field

from app.schemas.task import TaskResponse


class MenteeListItem(BaseModel):
    menteeId: str
    name: str
    grade: str | None = None
    subjects: list[str] = []
    todayTaskCount: int = 0
    todayCompletedCount: int = 0

class MenteeDetailResponse(BaseModel):
    menteeId: str
    name: str
    grade: str | None = None
    subjects: list[str] = []
    tasks: list[TaskResponse] = []
    completionRate: float = 0.0


class ReviewQueueItem(BaseModel):
    submissionId: str
    taskId: str
    taskTitle: str
    menteeName: str
    menteeId: str
    submissionType: str
    signalLight: str | None = None
    densityScore: int | None = None
    analysisStatus: str | None = None
    submittedAt: dt.datetime


class DashboardResponse(BaseModel):
    mentees: list[MenteeListItem]
    reviewQueue: list[ReviewQueueItem]


class JudgmentConfirmRequest(BaseModel):
    pass


class JudgmentModifyRequest(BaseModel):
    signalLight: str = Field(pattern="^(GREEN|YELLOW|RED)$", examples=["YELLOW"])
    score: int = Field(ge=0, le=100, examples=[65])
    reason: str = Field(min_length=1, max_length=500, examples=["필기 흔적이 부족하여 하향 조정"])


class JudgmentResponse(BaseModel):
    id: str
    analysisId: str
    mentorId: str
    originalSignalLight: str
    originalScore: int
    finalSignalLight: str
    finalScore: int
    reason: str | None = None
    isModified: bool

    model_config = {"from_attributes": True}


class FeedbackItemRequest(BaseModel):
    taskId: str
    detail: str = Field(min_length=1, max_length=1000)


class FeedbackCreateRequest(BaseModel):
    menteeId: str
    date: dt.date = Field(examples=["2026-02-03"])
    items: list[FeedbackItemRequest] = Field(min_length=1)
    summary: str | None = Field(default=None, max_length=500)
    isHighlighted: bool = False
    generalComment: str | None = Field(default=None, max_length=1000)


class FeedbackItemResponse(BaseModel):
    id: str
    taskId: str
    detail: str

    model_config = {"from_attributes": True}


class FeedbackResponse(BaseModel):
    id: str
    menteeId: str
    mentorId: str
    date: dt.date
    summary: str | None = None
    isHighlighted: bool
    generalComment: str | None = None
    items: list[FeedbackItemResponse] = []

    model_config = {"from_attributes": True}
