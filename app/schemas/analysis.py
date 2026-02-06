from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TraceTypesData(BaseModel):
    """풀이 흔적 유형별 비율"""
    underlineRatio: float = Field(default=0.0, description="밑줄/형광펜 비율 (0~1)")
    memoRatio: float = Field(default=0.0, description="메모/요약 비율 (0~1)")
    solutionRatio: float = Field(default=0.0, description="풀이 과정 비율 (0~1)")


class PartDensityItem(BaseModel):
    """파트별 밀도"""
    partNumber: int = Field(description="파트/문제 번호")
    partTitle: str = Field(description="파트/문제 제목")
    density: int = Field(description="밀도 점수 (0~100)")


class AnalysisResponse(BaseModel):
    """AI 분석 응답"""
    id: str = Field(description="분석 ID")
    submissionId: str = Field(description="제출물 ID")
    status: str = Field(description="분석 상태 (PROCESSING: 진행중, COMPLETED: 완료, FAILED: 실패)")
    signalLight: str | None = Field(default=None, description="신호등 (GREEN: 우수, YELLOW: 보통, RED: 보완필요)")
    densityScore: int | None = Field(default=None, description="전체 밀도 점수 (0~100)")
    writingRatio: float | None = Field(default=None, description="글씨 채움 비율 (0~1)")
    traceTypes: Any | None = Field(default=None, description="풀이 흔적 유형별 비율 (underlineRatio, memoRatio, solutionRatio)")
    partDensity: Any | None = Field(default=None, description="파트/문제별 밀도 분석 리스트")
    pageHeatmap: Any | None = Field(default=None, description="페이지 히트맵 데이터")
    summary: str | None = Field(default=None, description="1줄 요약")
    detailedAnalysis: str | None = Field(default=None, description="상세 분석 (최대 1000자)")
    mentorTip: str | None = Field(default=None, description="멘토 코칭 팁")
    createdAt: datetime = Field(description="생성 일시")
    updatedAt: datetime = Field(description="수정 일시")

    model_config = {"from_attributes": True}


class AnalysisStatusResponse(BaseModel):
    """분석 상태 응답"""
    id: str = Field(description="분석 ID")
    submissionId: str = Field(description="제출물 ID")
    status: str = Field(description="분석 상태 (PROCESSING/COMPLETED/FAILED)")


class AnalysisTriggerResponse(BaseModel):
    """분석 트리거 응답"""
    analysisId: str = Field(description="분석 ID")
    status: str = Field(description="분석 상태")


# ===== 오답 학습지 =====

class WrongAnswerSheetResponse(BaseModel):
    """오답 학습지 응답"""
    id: str = Field(description="오답 학습지 ID")
    submissionId: str = Field(description="제출물 ID")
    problemId: str = Field(description="문제 ID")
    problemNumber: int = Field(description="문제 번호")
    problemTitle: str = Field(description="문제 제목")
    originalAnswer: str | None = Field(default=None, description="멘티가 제출한 답")
    correctAnswer: str | None = Field(default=None, description="정답")
    explanation: str | None = Field(default=None, description="해설")
    relatedConcepts: list[str] = Field(default=[], description="관련 개념 태그 목록")
    practiceUrl: str | None = Field(default=None, description="연습 문제 URL")
    isCompleted: bool = Field(default=False, description="복습 완료 여부")
    completedAt: datetime | None = Field(default=None, description="복습 완료 일시")
    createdAt: datetime = Field(description="생성 일시")

    model_config = {"from_attributes": True}


class WrongAnswerSheetCompleteRequest(BaseModel):
    """오답 학습지 완료 요청"""
    isCompleted: bool = Field(default=True, description="복습 완료 여부")
