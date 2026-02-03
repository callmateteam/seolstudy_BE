from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AnalysisResponse(BaseModel):
    id: str
    submissionId: str
    status: str
    signalLight: str | None = None
    densityScore: int | None = None
    writingRatio: float | None = None
    traceTypes: Any | None = None
    pageHeatmap: Any | None = None
    summary: str | None = None
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
