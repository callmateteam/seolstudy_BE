from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProblemResponseCreate(BaseModel):
    problemId: str
    answer: str | None = Field(default=None, max_length=1000)
    textNote: str | None = Field(default=None, max_length=5000)
    highlightData: dict | None = None
    drawingUrl: str | None = None


class SubmissionCreateRequest(BaseModel):
    submissionType: str = Field(
        pattern="^(TEXT|DRAWING)$",
        examples=["TEXT"],
        description="제출 유형 (TEXT: 텍스트 입력, DRAWING: 그리기/이미지)",
    )
    textContent: str | None = Field(
        default=None,
        examples=["풀이: x^2 + 2x + 1 = (x+1)^2"],
        description="TEXT 모드일 때 텍스트 내용",
    )
    images: list[str] | None = Field(
        default=None,
        examples=[["https://s3.../image1.jpg"]],
        description="학습 인증 사진 S3 URL 목록 (옵셔널)",
    )
    studyTimeMinutes: int | None = Field(
        default=None, ge=0, le=1440,
        description="공부 시간(분)",
    )
    selfScoreCorrect: int | None = Field(default=None, ge=0, description="맞은 문제 수")
    selfScoreTotal: int | None = Field(default=None, ge=1, description="전체 문제 수")
    wrongQuestions: list[int] | None = Field(default=None, description="틀린 문제 번호 목록")
    comment: str | None = Field(
        default=None, max_length=1000,
        description="멘토에게 질문/코멘트",
    )
    problemResponses: list[ProblemResponseCreate] | None = Field(
        default=None,
        description="문제별 응답 (과제에 문제가 있는 경우)",
    )


class SelfScoreRequest(BaseModel):
    selfScoreCorrect: int = Field(ge=0, examples=[8], description="맞은 문제 수")
    selfScoreTotal: int = Field(ge=1, examples=[10], description="전체 문제 수")
    wrongQuestions: list[int] = Field(
        default=[],
        examples=[[3, 7]],
        description="틀린 문제 번호 목록",
    )


class ProblemResponseData(BaseModel):
    id: str
    problemId: str
    answer: str | None = None
    textNote: str | None = None
    highlightData: Any | None = None
    drawingUrl: str | None = None

    model_config = {"from_attributes": True}


class SubmissionResponse(BaseModel):
    id: str
    taskId: str
    menteeId: str
    submissionType: str
    textContent: str | None = None
    images: list[str]
    selfScoreCorrect: int | None = None
    selfScoreTotal: int | None = None
    wrongQuestions: list[int]
    comment: str | None = None
    problemResponses: list[ProblemResponseData] = []
    submittedAt: datetime

    @field_validator("problemResponses", mode="before")
    @classmethod
    def _coerce_responses(cls, v):
        return v if v is not None else []

    model_config = {"from_attributes": True}
