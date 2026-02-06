from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TraceTypesData(BaseModel):
    """풀이 흔적 유형별 비율"""
    underlineRatio: float = 0.0      # 밑줄/형광펜 비율 (%)
    memoRatio: float = 0.0           # 메모/요약 비율 (%)
    solutionRatio: float = 0.0       # 풀이 과정 비율 (%)


class PartDensityItem(BaseModel):
    """파트별 밀도"""
    partNumber: int
    partTitle: str
    density: int  # 0~100


class AnalysisResponse(BaseModel):
    id: str
    submissionId: str
    status: str
    signalLight: str | None = None
    densityScore: int | None = None
    writingRatio: float | None = None
    traceTypes: Any | None = None       # TraceTypesData
    partDensity: Any | None = None      # list[PartDensityItem]
    pageHeatmap: Any | None = None
    summary: str | None = None          # 1줄 요약
    detailedAnalysis: str | None = None  # 상세 분석 (최대 1000자)
    mentorTip: str | None = None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


class AnalysisStatusResponse(BaseModel):
    id: str
    submissionId: str
    status: str


class AnalysisTriggerResponse(BaseModel):
    analysisId: str
    status: str


# ===== 오답 학습지 =====

class WrongAnswerSheetResponse(BaseModel):
    id: str
    submissionId: str
    problemId: str
    problemNumber: int
    problemTitle: str
    originalAnswer: str | None = None
    correctAnswer: str | None = None
    explanation: str | None = None
    relatedConcepts: list[str] = []
    practiceUrl: str | None = None
    isCompleted: bool = False
    completedAt: datetime | None = None
    createdAt: datetime

    model_config = {"from_attributes": True}


class WrongAnswerSheetCompleteRequest(BaseModel):
    isCompleted: bool = True
