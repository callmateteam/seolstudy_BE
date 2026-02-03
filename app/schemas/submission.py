from datetime import datetime

from pydantic import BaseModel, Field


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
        description="DRAWING 모드일 때 S3 이미지 URL 목록",
    )


class SelfScoreRequest(BaseModel):
    selfScoreCorrect: int = Field(ge=0, examples=[8], description="맞은 문제 수")
    selfScoreTotal: int = Field(ge=1, examples=[10], description="전체 문제 수")
    wrongQuestions: list[int] = Field(
        default=[],
        examples=[[3, 7]],
        description="틀린 문제 번호 목록",
    )


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
    submittedAt: datetime

    model_config = {"from_attributes": True}
