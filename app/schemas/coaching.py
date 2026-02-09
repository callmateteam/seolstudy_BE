import datetime as dt
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.analysis import AnalysisResponse
from app.schemas.submission import SubmissionResponse


class CoachingDetailResponse(BaseModel):
    submission: SubmissionResponse = Field(description="제출물 정보")
    analysis: AnalysisResponse | None = Field(default=None, description="AI 분석 결과")
    taskTitle: str = Field(description="과제 제목")
    menteeName: str = Field(description="멘티 이름")


class AiDraftResponse(BaseModel):
    submissionId: str = Field(description="제출물 ID")
    draft: str = Field(description="AI가 생성한 피드백 초안")
    suggestedSignalLight: str | None = Field(default=None, description="제안 신호등 (GREEN/YELLOW/RED)")
    suggestedScore: int | None = Field(default=None, description="제안 밀도 점수 (0~100)")


class RecommendationItem(BaseModel):
    materialId: str = Field(description="학습지 ID")
    title: str = Field(description="학습지 제목")
    subject: str = Field(description="과목 (KOREAN/ENGLISH/MATH)")
    abilityTags: list[str] = Field(description="능력 태그 목록")
    difficulty: int | None = Field(default=None, description="난이도 (1~5)")
    reason: str = Field(description="추천 이유")


class RecommendationsResponse(BaseModel):
    submissionId: str = Field(description="제출물 ID")
    recommendations: list[RecommendationItem] = Field(description="추천 학습지 목록")


class AssignMaterialRequest(BaseModel):
    menteeId: str = Field(description="멘티 프로필 ID")
    materialId: str = Field(description="배정할 학습지 ID")
    date: str = Field(examples=["2026-02-03"], description="배정 날짜 (YYYY-MM-DD)")
    title: str | None = Field(default=None, max_length=200, description="과제 제목 (미입력 시 학습지 제목 사용)")


# ===== Coaching Session (코칭센터 종합 조회) =====


class MenteeBasicInfo(BaseModel):
    """멘티 기본 정보"""
    id: str = Field(description="멘티 프로필 ID")
    name: str = Field(description="멘티 이름")
    grade: str = Field(description="학년 (예: '고1')")
    school: str | None = Field(default=None, description="학교명")


class ProblemResponseDetail(BaseModel):
    """문제별 응답 상세 (형광펜, 메모, 그림 포함)"""
    problemId: str = Field(description="문제 ID")
    problemNumber: int = Field(description="문제 번호")
    problemTitle: str = Field(description="문제 제목")
    answer: str | None = Field(default=None, description="멘티가 선택한 답")
    isCorrect: bool | None = Field(default=None, description="자동채점 결과 (null=채점불가, true=정답, false=오답)")
    textNote: str | None = Field(default=None, description="텍스트 메모")
    highlightData: Any | None = Field(default=None, description="형광펜 위치 데이터 (JSON)")
    drawingUrl: str | None = Field(default=None, description="그림 이미지 S3 URL")


class SubmissionDetail(BaseModel):
    """제출 상세 (코멘트, 인증샷, 문제 응답 포함)"""
    id: str = Field(description="제출물 ID")
    comment: str | None = Field(default=None, description="멘토에게 남긴 질문/코멘트")
    images: list[str] = Field(default=[], description="학습 인증 사진 URL 목록")
    textContent: str | None = Field(default=None, description="텍스트 제출 내용")
    problemResponses: list[ProblemResponseDetail] = Field(default=[], description="문제별 응답 목록")
    selfScoreCorrect: int | None = Field(default=None, description="자기채점 맞은 문제 수")
    selfScoreTotal: int | None = Field(default=None, description="자기채점 전체 문제 수")
    wrongQuestions: list[int] = Field(default=[], description="틀린 문제 번호 목록")
    submittedAt: dt.datetime = Field(description="제출 일시")

    @field_validator("problemResponses", mode="before")
    @classmethod
    def _coerce_responses(cls, v):
        return v if v is not None else []


class PartDensityItem(BaseModel):
    """문제별 밀도 분석"""
    problemNumber: int = Field(description="문제 번호")
    problemTitle: str = Field(description="문제 제목")
    density: int = Field(description="밀도 점수 (0~100)")


class TraceTypesDetail(BaseModel):
    """풀이 흔적 유형별 비율"""
    underlineRatio: float = Field(default=0.0, description="밑줄/형광펜 비율 (0~1)")
    memoRatio: float = Field(default=0.0, description="메모 비율 (0~1)")
    solutionRatio: float = Field(default=0.0, description="풀이 과정 비율 (0~1)")


class AnalysisDetail(BaseModel):
    """AI 분석 상세"""
    id: str = Field(description="분석 ID")
    status: str = Field(description="분석 상태 (PROCESSING/COMPLETED/FAILED)")
    densityScore: int | None = Field(default=None, description="전체 밀도 점수 (0~100)")
    signalLight: str | None = Field(default=None, description="신호등 (GREEN: 우수, YELLOW: 보통, RED: 보완필요)")
    summary: str | None = Field(default=None, description="1줄 요약")
    detailedAnalysis: str | None = Field(default=None, description="상세 분석 (최대 1000자)")
    partDensity: list[PartDensityItem] = Field(default=[], description="문제별 밀도 분석")
    traceTypes: TraceTypesDetail | None = Field(default=None, description="풀이 흔적 유형별 비율")
    mentorTip: str | None = Field(default=None, description="멘토 코칭 팁")

    @field_validator("partDensity", mode="before")
    @classmethod
    def _coerce_part_density(cls, v):
        return v if v is not None else []


class RecommendedMaterial(BaseModel):
    """추천 보완 학습지"""
    id: str = Field(description="학습지 ID")
    title: str = Field(description="학습지 제목")
    subject: str = Field(description="과목")
    abilityTags: list[str] = Field(default=[], description="능력 태그 목록")
    difficulty: int | None = Field(default=None, description="난이도 (1~5)")
    isAssigned: bool = Field(default=False, description="이미 다음날 과제로 배정되었는지 여부")


class TaskCoachingItem(BaseModel):
    """과제별 코칭 데이터"""
    id: str = Field(description="과제 ID")
    title: str = Field(description="과제 제목")
    subject: str = Field(description="과목")
    abilityTag: str | None = Field(default=None, description="능력 태그")
    tags: list[str] = Field(default=[], description="멘토 칩 태그 목록")
    status: str = Field(description="과제 상태 (PENDING/SUBMITTED/COMPLETED)")
    submission: SubmissionDetail | None = Field(default=None, description="제출물 정보 (미제출 시 null)")
    analysis: AnalysisDetail | None = Field(default=None, description="AI 분석 결과 (미분석 시 null)")
    aiDraft: str | None = Field(default=None, description="AI 피드백 초안")
    recommendedMaterials: list[RecommendedMaterial] = Field(default=[], description="추천 보완 학습지 목록")
    detailFeedback: str | None = Field(default=None, description="저장된 상세 피드백 (멘토 작성)")


class CoachingSessionResponse(BaseModel):
    """코칭센터 세션 종합 응답"""
    mentee: MenteeBasicInfo = Field(description="멘티 정보")
    date: dt.date = Field(description="코칭 날짜")
    tasks: list[TaskCoachingItem] = Field(description="해당일 과제 목록 (제출물/분석/피드백 포함)")
    dailySummary: str | None = Field(default=None, description="학습 총평 (당일 종합 피드백)")


class TaskFeedbackRequest(BaseModel):
    """과제별 상세 피드백 저장 요청"""
    taskId: str = Field(description="과제 ID")
    detail: str = Field(min_length=1, max_length=2000, description="상세 피드백 내용")


class DailySummaryRequest(BaseModel):
    """학습 총평 저장 요청"""
    menteeId: str = Field(description="멘티 프로필 ID")
    date: dt.date = Field(examples=["2026-02-01"], description="날짜 (YYYY-MM-DD)")
    generalComment: str = Field(min_length=1, max_length=2000, description="학습 총평 내용")
