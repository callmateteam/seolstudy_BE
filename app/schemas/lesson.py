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


class LessonProblemCreate(BaseModel):
    """학습 문제 생성 요청"""
    number: int = Field(ge=1, description="문제 번호 (1부터 시작)")
    title: str = Field(min_length=1, max_length=500, description="문제 제목/질문")
    content: str | None = Field(default=None, max_length=5000, description="보조 지문이나 <보기>")
    options: list[dict] | None = Field(default=None, description="객관식 선지 목록")
    correctAnswer: str | None = Field(default=None, max_length=200, description="정답")
    displayOrder: int = Field(default=0, ge=0, description="표시 순서")


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
    content: str | None = Field(
        default=None,
        max_length=10000,
        description="추출된 지문/본문 텍스트",
    )
    problems: list[LessonProblemCreate] | None = Field(
        default=None,
        description="문제 목록 (PDF 자동 추출 또는 직접 입력)",
    )
    targetStudyMinutes: int | None = Field(
        default=None, ge=0, le=1440,
        description="목표 공부 시간 (분)",
        examples=[60],
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
    content: str | None = Field(default=None, max_length=10000)
    targetStudyMinutes: int | None = Field(default=None, ge=0, le=1440)


class LessonProblemResponse(BaseModel):
    """학습 문제 응답"""
    id: str
    number: int
    title: str
    content: str | None = None
    options: list[dict] | None = None
    correctAnswer: str | None = None
    displayOrder: int = 0

    model_config = {"from_attributes": True}


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
    content: str | None = None
    targetStudyMinutes: int | None = None
    problems: list[LessonProblemResponse] = []
    problemCount: int = 0
    status: str
    createdAt: dt.datetime


class LessonListResponse(BaseModel):
    """등록된 학습 목록 응답"""
    lessons: list[LessonResponse]
    total: int


class ParsedProblem(BaseModel):
    """GPT가 PDF에서 추출한 개별 문제"""
    number: int = Field(description="문제 번호")
    title: str = Field(description="문제 제목/질문")
    content: str | None = Field(default=None, description="보조 지문이나 <보기>")
    options: list[dict] | None = Field(default=None, description="객관식 선지 목록")
    correctAnswer: str | None = Field(default=None, description="정답 (있는 경우)")


class LessonUploadResponse(BaseModel):
    """학습지 업로드 응답"""
    materialUrl: str = Field(description="S3 업로드 URL")
    originalName: str = Field(description="원본 파일명")
    size: int = Field(description="파일 크기 (bytes)")
    parsed: bool = Field(default=False, description="지문/문제 자동 분리 성공 여부")
    content: str | None = Field(default=None, description="추출된 지문/본문 텍스트")
    problems: list[ParsedProblem] | None = Field(default=None, description="추출된 문제 목록")
