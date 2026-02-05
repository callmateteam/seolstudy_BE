import datetime as dt

from pydantic import BaseModel, Field

from app.schemas.task import TaskResponse


class MenteeListItem(BaseModel):
    menteeId: str
    name: str
    grade: str | None = None
    subjects: list[str] = []
    completionRate: float = 0.0       # 전체 과제 완수율 %
    recentDensity: float | None = None  # 어제 밀도 %

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
    subject: str                       # 과목
    abilityTag: str | None = None      # 역량
    submittedAt: dt.datetime           # 제출시각
    elapsedMinutes: int = 0            # 경과시간 (분)
    densityScore: float | None = None  # AI 밀도 %


class CommentQueueItem(BaseModel):
    """코멘트 답변 대기열 아이템"""
    commentId: str
    menteeId: str
    menteeName: str
    content: str                       # 코멘트 내용
    createdAt: dt.datetime             # 등록시각
    elapsedMinutes: int = 0            # 경과시간 (분)
    hasReply: bool = False             # 답변 완료 여부


class CommentReplyRequest(BaseModel):
    """코멘트 답변 요청"""
    reply: str = Field(min_length=1, max_length=500, examples=["좋은 질문이에요. 해당 문제는..."])


class DashboardResponse(BaseModel):
    mentees: list[MenteeListItem]           # 담당 멘티 (최대 2명)
    reviewQueue: list[ReviewQueueItem]      # 과제 검토 대기열
    commentQueue: list[CommentQueueItem]    # 코멘트 답변 대기열


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
