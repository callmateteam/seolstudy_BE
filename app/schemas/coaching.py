import datetime as dt
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.analysis import AnalysisResponse
from app.schemas.submission import SubmissionResponse


class CoachingDetailResponse(BaseModel):
    submission: SubmissionResponse
    analysis: AnalysisResponse | None = None
    taskTitle: str
    menteeName: str


class AiDraftResponse(BaseModel):
    submissionId: str
    draft: str
    suggestedSignalLight: str | None = None
    suggestedScore: int | None = None


class RecommendationItem(BaseModel):
    materialId: str
    title: str
    subject: str
    abilityTags: list[str]
    difficulty: int | None = None
    reason: str


class RecommendationsResponse(BaseModel):
    submissionId: str
    recommendations: list[RecommendationItem]


class AssignMaterialRequest(BaseModel):
    menteeId: str
    materialId: str
    date: str = Field(examples=["2026-02-03"])
    title: str | None = Field(default=None, max_length=200)


# ===== Coaching Session (코칭센터 종합 조회) =====


class MenteeBasicInfo(BaseModel):
    id: str
    name: str
    grade: str
    school: str | None = None


class ProblemResponseDetail(BaseModel):
    """문제별 응답 상세 (형광펜, 메모, 그림 포함)"""
    problemId: str
    problemNumber: int
    problemTitle: str
    answer: str | None = None
    textNote: str | None = None
    highlightData: Any | None = None
    drawingUrl: str | None = None


class SubmissionDetail(BaseModel):
    """제출 상세 (코멘트, 인증샷, 문제 응답 포함)"""
    id: str
    comment: str | None = None
    images: list[str] = []
    textContent: str | None = None
    problemResponses: list[ProblemResponseDetail] = []
    selfScoreCorrect: int | None = None
    selfScoreTotal: int | None = None
    wrongQuestions: list[int] = []
    submittedAt: dt.datetime

    @field_validator("problemResponses", mode="before")
    @classmethod
    def _coerce_responses(cls, v):
        return v if v is not None else []


class PartDensityItem(BaseModel):
    """문제별 밀도 분석"""
    problemNumber: int
    problemTitle: str
    density: int  # 0~100


class TraceTypesDetail(BaseModel):
    """풀이 흔적 유형별 비율"""
    underlineRatio: float = 0.0
    memoRatio: float = 0.0
    solutionRatio: float = 0.0


class AnalysisDetail(BaseModel):
    """AI 분석 상세"""
    id: str
    status: str
    densityScore: int | None = None
    signalLight: str | None = None
    summary: str | None = None  # 1줄 요약
    detailedAnalysis: str | None = None  # 상세 분석 (최대 1000자)
    partDensity: list[PartDensityItem] = []  # 문제별 밀도
    traceTypes: TraceTypesDetail | None = None
    mentorTip: str | None = None

    @field_validator("partDensity", mode="before")
    @classmethod
    def _coerce_part_density(cls, v):
        return v if v is not None else []


class RecommendedMaterial(BaseModel):
    """추천 보완 학습지"""
    id: str
    title: str
    subject: str
    abilityTags: list[str] = []
    difficulty: int | None = None
    isAssigned: bool = False


class TaskCoachingItem(BaseModel):
    """과제별 코칭 데이터"""
    id: str
    title: str
    subject: str
    abilityTag: str | None = None
    tags: list[str] = []
    status: str
    submission: SubmissionDetail | None = None
    analysis: AnalysisDetail | None = None
    aiDraft: str | None = None
    recommendedMaterials: list[RecommendedMaterial] = []
    detailFeedback: str | None = None  # 저장된 상세 피드백


class CoachingSessionResponse(BaseModel):
    """코칭센터 세션 종합 응답"""
    mentee: MenteeBasicInfo
    date: dt.date
    tasks: list[TaskCoachingItem]
    dailySummary: str | None = None  # 학습 총평


class TaskFeedbackRequest(BaseModel):
    """과제별 상세 피드백 저장 요청"""
    taskId: str
    detail: str = Field(min_length=1, max_length=2000)


class DailySummaryRequest(BaseModel):
    """학습 총평 저장 요청"""
    menteeId: str
    date: dt.date = Field(examples=["2026-02-01"])
    generalComment: str = Field(min_length=1, max_length=2000)
