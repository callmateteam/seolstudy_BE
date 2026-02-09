from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProblemResponseCreate(BaseModel):
    """문제별 응답 생성"""
    problemId: str = Field(description="문제 ID")
    answer: str | None = Field(default=None, max_length=1000, description="선택한 답")
    textNote: str | None = Field(default=None, max_length=5000, description="텍스트 메모")
    highlightData: dict | None = Field(default=None, description="형광펜 위치 데이터 (JSON)")
    drawingUrl: str | None = Field(default=None, description="그림 이미지 S3 URL")


class SubmissionCreateRequest(BaseModel):
    """제출물 생성 요청"""
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
        description="학습 인증 사진 S3 URL 목록",
    )
    studyTimeMinutes: int | None = Field(
        default=None, ge=0, le=1440,
        description="공부 시간 (분)",
    )
    selfScoreCorrect: int | None = Field(default=None, ge=0, description="자기채점 맞은 문제 수")
    selfScoreTotal: int | None = Field(default=None, ge=1, description="자기채점 전체 문제 수")
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
    """자기채점 요청"""
    selfScoreCorrect: int = Field(ge=0, examples=[8], description="맞은 문제 수")
    selfScoreTotal: int = Field(ge=1, examples=[10], description="전체 문제 수")
    wrongQuestions: list[int] = Field(
        default=[],
        examples=[[3, 7]],
        description="틀린 문제 번호 목록",
    )


class ProblemResponseData(BaseModel):
    """문제별 응답 데이터"""
    id: str = Field(description="응답 ID")
    problemId: str = Field(description="문제 ID")
    answer: str | None = Field(default=None, description="선택한 답")
    isCorrect: bool | None = Field(default=None, description="자동채점 결과 (null=채점불가, true=정답, false=오답)")
    textNote: str | None = Field(default=None, description="텍스트 메모")
    highlightData: Any | None = Field(default=None, description="형광펜 위치 데이터")
    drawingUrl: str | None = Field(default=None, description="그림 이미지 S3 URL")

    model_config = {"from_attributes": True}


class SubmissionResponse(BaseModel):
    """제출물 응답"""
    id: str = Field(description="제출물 ID")
    taskId: str = Field(description="과제 ID")
    menteeId: str = Field(description="멘티 프로필 ID")
    submissionType: str = Field(description="제출 유형 (TEXT/DRAWING)")
    textContent: str | None = Field(default=None, description="텍스트 제출 내용")
    images: list[str] = Field(description="학습 인증 사진 URL 목록")
    selfScoreCorrect: int | None = Field(default=None, description="자기채점 맞은 문제 수")
    selfScoreTotal: int | None = Field(default=None, description="자기채점 전체 문제 수")
    wrongQuestions: list[int] = Field(description="틀린 문제 번호 목록")
    comment: str | None = Field(default=None, description="멘토에게 남긴 질문/코멘트")
    problemResponses: list[ProblemResponseData] = Field(default=[], description="문제별 응답 목록")
    submittedAt: datetime = Field(description="제출 일시")

    @field_validator("problemResponses", mode="before")
    @classmethod
    def _coerce_responses(cls, v):
        return v if v is not None else []

    model_config = {"from_attributes": True}
