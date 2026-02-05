from datetime import datetime

from pydantic import BaseModel, Field


class MentorInfo(BaseModel):
    """담당 멘토 정보"""
    id: str
    name: str
    university: str
    department: str


class SubjectStat(BaseModel):
    """과목별 통계"""
    subject: str
    abilityTags: list[str] = []          # 해당 과목 과제들의 능력 태그
    totalTasks: int = 0                   # 전체 과제 수
    completedTasks: int = 0               # 완료한 과제 수
    completionRate: float = 0.0           # 달성률 (%)
    avgDensityScore: float | None = None  # 평균 밀도 점수


class ActivitySummary(BaseModel):
    """활동 요약"""
    activeDays: int = 0           # 활동 일수
    totalCompletedTasks: int = 0  # 총 완수 과제
    overallCompletionRate: float = 0.0  # 전체 달성률 (%)


class MyPageResponse(BaseModel):
    """마이 페이지 응답"""
    # 기본 정보
    id: str
    role: str
    name: str
    profileImage: str | None = None
    joinedAt: datetime

    # 멘티 전용 정보
    school: str | None = None
    grade: str | None = None
    subjects: list[str] = []
    mentor: MentorInfo | None = None

    # 과목별 달성률
    subjectStats: list[SubjectStat] = []

    # 활동 요약
    activitySummary: ActivitySummary | None = None


class MyPageUpdateRequest(BaseModel):
    """마이 페이지 수정 요청 (이름, 학교만 수정 가능)"""
    name: str | None = Field(default=None, min_length=1, max_length=50)
    school: str | None = Field(default=None, max_length=100)
