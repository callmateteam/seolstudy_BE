import datetime as dt

from pydantic import BaseModel, Field


# 과목별 역량 태그 정의
ABILITY_TAGS = {
    "KOREAN": ["문해력", "비문학", "문학", "화법과작문", "언어와매체"],
    "ENGLISH": ["독해", "듣기", "어휘", "문법", "빈칸추론"],
    "MATH": ["미적분", "확률과통계", "기하", "수열", "함수"],
}


class AbilityTagsResponse(BaseModel):
    """과목별 역량 태그 응답"""
    subject: str
    tags: list[str]


class LessonCreateRequest(BaseModel):
    """학습 등록 요청"""
    menteeId: str
    date: dt.date = Field(examples=["2026-02-01"])
    subject: str = Field(pattern="^(KOREAN|ENGLISH|MATH)$", examples=["KOREAN"])
    abilityTags: list[str] = Field(
        max_length=3,
        examples=[["문해력", "비문학"]],
        description="역량 태그 (최대 3개, 기본 제공 또는 직접 입력)",
    )
    title: str = Field(min_length=1, max_length=200, examples=["비문학 독해 3회차"])
    goal: str | None = Field(
        default=None,
        max_length=500,
        examples=["이 과제의 학습 목표를 작성해주세요"],
    )
    materialId: str | None = Field(
        default=None,
        description="기존 학습지 ID (관리자 등록 학습지)",
    )
    materialUrl: str | None = Field(
        default=None,
        description="직접 업로드한 학습지 URL",
    )


class LessonUpdateRequest(BaseModel):
    """학습 수정 요청"""
    subject: str | None = Field(
        default=None, pattern="^(KOREAN|ENGLISH|MATH)$"
    )
    abilityTags: list[str] | None = Field(default=None, max_length=3)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    goal: str | None = Field(default=None, max_length=500)
    materialId: str | None = None
    materialUrl: str | None = None


class LessonResponse(BaseModel):
    """학습 응답"""
    id: str
    menteeId: str
    date: dt.date
    subject: str
    abilityTags: list[str] = []
    title: str
    goal: str | None = None
    materialId: str | None = None
    materialUrl: str | None = None
    status: str
    createdAt: dt.datetime


class LessonListResponse(BaseModel):
    """등록된 학습 목록 응답"""
    lessons: list[LessonResponse]
    total: int


class LessonUploadResponse(BaseModel):
    """학습지 업로드 응답"""
    materialUrl: str
    originalName: str
    size: int
    # 향후 지문/문제 분리 결과
    parsed: bool = False
    content: str | None = None      # 지문 내용 (OCR 추출)
    problems: list[dict] | None = None  # 문제 목록
