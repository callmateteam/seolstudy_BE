import datetime as dt
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ===== Problem schemas =====

class TaskProblemCreateRequest(BaseModel):
    """문제 생성 요청 (멘토 전용)"""
    number: int = Field(ge=1, examples=[1], description="문제 번호 (1부터 시작)")
    title: str = Field(min_length=1, max_length=500, examples=["다음 글을 읽고 물음에 답하시오."], description="문제 제목")
    content: str | None = Field(default=None, max_length=5000, description="문제 본문/지문")
    options: list[dict] | None = Field(
        default=None,
        examples=[[{"label": "1", "text": "선지 내용"}]],
        description="선지 목록 (객관식)",
    )
    correctAnswer: str | None = Field(default=None, max_length=200, description="정답 (멘티에게 숨김)")
    displayOrder: int = Field(default=0, ge=0, description="표시 순서")


class TaskProblemUpdateRequest(BaseModel):
    """문제 수정 요청"""
    number: int | None = Field(default=None, ge=1, description="문제 번호")
    title: str | None = Field(default=None, min_length=1, max_length=500, description="문제 제목")
    content: str | None = Field(default=None, description="문제 본문/지문")
    options: list[dict] | None = Field(default=None, description="선지 목록")
    correctAnswer: str | None = Field(default=None, description="정답")
    displayOrder: int | None = Field(default=None, ge=0, description="표시 순서")


class TaskProblemResponse(BaseModel):
    """문제 응답 (멘티용 - 정답 제외)"""
    id: str = Field(description="문제 ID")
    taskId: str = Field(description="과제 ID")
    number: int = Field(description="문제 번호")
    title: str = Field(description="문제 제목")
    content: str | None = Field(default=None, description="문제 본문/지문")
    options: Any | None = Field(default=None, description="선지 목록")
    displayOrder: int = Field(description="표시 순서")

    model_config = {"from_attributes": True}


class TaskProblemWithAnswerResponse(TaskProblemResponse):
    """문제 응답 (멘토용 - 정답 포함)"""
    correctAnswer: str | None = Field(default=None, description="정답")


# ===== Task schemas =====

class TaskCreateRequest(BaseModel):
    """과제 생성 요청"""
    date: dt.date = Field(examples=["2026-02-03"], description="과제 날짜 (YYYY-MM-DD)")
    title: str = Field(min_length=1, max_length=200, examples=["수학 미적분 p.32~35"], description="과제 제목")
    goal: str | None = Field(default=None, max_length=500, examples=["미분 개념 정리"], description="학습 목표")
    subject: str = Field(pattern="^(KOREAN|ENGLISH|MATH)$", examples=["MATH"], description="과목 (KOREAN/ENGLISH/MATH)")
    abilityTag: str | None = Field(default=None, max_length=50, examples=["미적분"], description="능력 태그")
    materialType: str | None = Field(
        default=None, pattern="^(COLUMN|PDF)$", examples=["PDF"], description="학습지 유형 (COLUMN/PDF)"
    )
    materialId: str | None = Field(default=None, description="연결된 학습지 ID")
    materialUrl: str | None = Field(default=None, description="학습지 URL (PDF 다운로드용)")
    repeat: bool = Field(default=False, description="반복 과제 여부")
    repeatDays: list[str] | None = Field(
        default=None,
        description="반복 요일 목록 (MON/TUE/WED/THU/FRI/SAT/SUN)",
        examples=[["MON", "WED", "FRI"]],
    )
    targetStudyMinutes: int | None = Field(
        default=None, ge=0, le=1440,
        description="목표 공부 시간 (분)",
        examples=[90],
    )
    memo: str | None = Field(default=None, max_length=1000, examples=["풀이 과정에 집중하기"], description="메모")
    tags: list[str] = Field(default=[], examples=[["국어", "문해력", "비문학"]], description="멘토 칩 태그 목록")
    keyPoints: str | None = Field(default=None, max_length=5000, description="핵심 정리 (멘토 작성)")
    content: str | None = Field(default=None, max_length=10000, description="지문/본문 (멘토 작성)")
    problems: list[TaskProblemCreateRequest] | None = Field(
        default=None, description="문제 목록 (멘토 전용)",
    )
    displayOrder: int = Field(default=0, ge=0, description="표시 순서")


class TaskUpdateRequest(BaseModel):
    """과제 수정 요청"""
    title: str | None = Field(default=None, min_length=1, max_length=200, description="과제 제목")
    goal: str | None = Field(default=None, description="학습 목표")
    subject: str | None = Field(default=None, pattern="^(KOREAN|ENGLISH|MATH)$", description="과목")
    abilityTag: str | None = Field(default=None, description="능력 태그")
    materialType: str | None = Field(default=None, pattern="^(COLUMN|PDF)$", description="학습지 유형")
    materialId: str | None = Field(default=None, description="연결된 학습지 ID")
    materialUrl: str | None = Field(default=None, description="학습지 URL")
    repeat: bool | None = Field(default=None, description="반복 과제 여부")
    repeatDays: list[str] | None = Field(default=None, description="반복 요일 목록")
    targetStudyMinutes: int | None = Field(default=None, ge=0, le=1440, description="목표 공부 시간 (분)")
    memo: str | None = Field(default=None, description="메모")
    tags: list[str] | None = Field(default=None, description="멘토 칩 태그 목록")
    keyPoints: str | None = Field(default=None, description="핵심 정리")
    content: str | None = Field(default=None, description="지문/본문")
    displayOrder: int | None = Field(default=None, ge=0, description="표시 순서")


class StudyTimeRequest(BaseModel):
    """공부 시간 기록 요청"""
    minutes: int = Field(ge=0, le=1440, examples=[45], description="공부 시간 (분)")


class BookmarkRequest(BaseModel):
    """북마크 토글 요청"""
    isBookmarked: bool = Field(description="북마크 설정 여부")


class TaskResponse(BaseModel):
    """과제 응답"""
    id: str = Field(description="과제 ID")
    menteeId: str = Field(description="멘티 프로필 ID")
    createdByMentorId: str | None = Field(default=None, description="생성한 멘토 ID (멘토 생성 과제인 경우)")
    date: dt.date = Field(description="과제 날짜")
    title: str = Field(description="과제 제목")
    goal: str | None = Field(default=None, description="학습 목표")
    subject: str = Field(description="과목 (KOREAN/ENGLISH/MATH)")
    abilityTag: str | None = Field(default=None, description="능력 태그")
    materialType: str | None = Field(default=None, description="학습지 유형 (COLUMN/PDF)")
    materialId: str | None = Field(default=None, description="연결된 학습지 ID")
    materialUrl: str | None = Field(default=None, description="학습지 URL")
    isLocked: bool = Field(description="잠금 여부 (멘토 생성 과제는 멘티가 수정 불가)")
    status: str = Field(description="상태 (PENDING: 대기, SUBMITTED: 제출됨, COMPLETED: 완료)")
    studyTimeMinutes: int | None = Field(default=None, description="실제 공부 시간 (분)")
    repeat: bool = Field(default=False, description="반복 과제 여부")
    repeatDays: list[str] = Field(default=[], description="반복 요일 목록")
    targetStudyMinutes: int | None = Field(default=None, description="목표 공부 시간 (분)")
    memo: str | None = Field(default=None, description="메모")
    tags: list[str] = Field(default=[], description="멘토 칩 태그 목록")
    keyPoints: str | None = Field(default=None, description="핵심 정리")
    content: str | None = Field(default=None, description="지문/본문")
    isBookmarked: bool = Field(default=False, description="북마크 여부 (멘티)")
    problems: list[TaskProblemResponse] = Field(default=[], description="문제 목록")
    problemCount: int = Field(default=0, description="문제 수")
    createdBy: str = Field(description="생성자 (MENTEE/MENTOR)")
    displayOrder: int = Field(description="표시 순서")

    @field_validator("problems", mode="before")
    @classmethod
    def _coerce_problems(cls, v):
        return v if v is not None else []

    model_config = {"from_attributes": True}
