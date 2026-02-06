from datetime import datetime

from pydantic import BaseModel, Field


class MentorInfo(BaseModel):
    """담당 멘토 정보"""
    id: str = Field(description="멘토 프로필 ID")
    name: str = Field(description="멘토 이름")
    university: str = Field(description="대학교명")
    department: str = Field(description="학과명")


class SubjectStat(BaseModel):
    """과목별 통계"""
    subject: str = Field(description="과목명 (KOREAN, ENGLISH, MATH)")
    abilityTags: list[str] = Field(default=[], description="해당 과목 과제들의 능력 태그")
    totalTasks: int = Field(default=0, description="전체 과제 수")
    completedTasks: int = Field(default=0, description="완료한 과제 수")
    completionRate: float = Field(default=0.0, description="달성률 (0~100%, 예: 75.0)")
    avgDensityScore: float | None = Field(default=None, description="평균 밀도 점수 (0~100)")


class ActivitySummary(BaseModel):
    """활동 요약"""
    activeDays: int = Field(default=0, description="총 활동 일수 (과제 완료 또는 피드백 작성한 날)")
    consecutiveDays: int = Field(default=0, description="연속 활동일 (오늘 기준)")
    totalCompletedTasks: int = Field(default=0, description="총 완수 과제 수 (멘티)")
    totalFeedbacks: int = Field(default=0, description="총 피드백 수 (멘티: 받은 수, 멘토: 작성한 수)")
    overallCompletionRate: float = Field(default=0.0, description="전체 달성률 (0~100%, 멘티 전용)")


class MyPageResponse(BaseModel):
    """마이 페이지 응답"""
    # 기본 정보
    id: str = Field(description="사용자 ID")
    role: str = Field(description="역할 (MENTEE, MENTOR, PARENT)")
    name: str = Field(description="이름")
    avatar: int = Field(default=1, description="아바타 번호 (1~20, role+avatar로 프론트에서 이미지 조합)")
    profileImage: str | None = Field(default=None, description="프로필 이미지 URL (S3)")
    joinedAt: datetime = Field(description="가입일시")

    # 멘티 전용 정보
    school: str | None = Field(default=None, description="학교명 (멘티)")
    grade: str | None = Field(default=None, description="학년 (멘티, 예: '고1')")
    subjects: list[str] = Field(default=[], description="수강 과목 목록 (멘티/멘토)")
    mentor: MentorInfo | None = Field(default=None, description="담당 멘토 정보 (멘티)")

    # 멘토 전용 정보
    university: str | None = Field(default=None, description="대학교명 (멘토)")
    department: str | None = Field(default=None, description="학과명 (멘토)")

    # 과목별 달성률 (멘티)
    subjectStats: list[SubjectStat] = Field(default=[], description="과목별 통계 (멘티)")

    # 활동 요약 (멘티/멘토 모두)
    activitySummary: ActivitySummary | None = Field(default=None, description="활동 요약")


class MyPageUpdateRequest(BaseModel):
    """마이 페이지 수정 요청"""
    name: str | None = Field(default=None, min_length=1, max_length=50, description="이름")
    avatar: int | None = Field(default=None, ge=1, le=20, description="아바타 번호 (1~20)")
    school: str | None = Field(default=None, max_length=100, description="학교명 (멘티 전용)")
