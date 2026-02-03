from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.analysis import AnalysisResponse
from app.schemas.material import MaterialResponse
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
