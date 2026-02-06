from pydantic import BaseModel


class MentorBasicInfo(BaseModel):
    """멘토 기본 정보 (학부모용)"""
    id: str
    name: str
    avatar: int = 1
    university: str
    department: str


class ParentDashboardResponse(BaseModel):
    """학부모 대시보드 응답"""
    # 자녀 정보
    menteeName: str
    menteeGrade: str | None = None
    menteeSubjects: list[str] = []

    # 오늘 학습 현황
    todayTaskCount: int = 0
    todayCompletedCount: int = 0
    todayCompletionRate: float = 0.0  # 오늘 과제 완수율 (0~1)

    # 이번주 학습 밀도
    weeklyDensityScore: float | None = None  # 이번주 평균 밀도 (0~100)

    # 멘토 정보
    mentor: MentorBasicInfo | None = None

    # 최근 피드백
    recentFeedbackCount: int = 0


class DailyCompletionRate(BaseModel):
    """일별 완수율"""
    date: str
    total: int
    completed: int
    rate: float


class MenteeStatusResponse(BaseModel):
    """자녀 학습 현황 응답"""
    weeklyCompletionRates: list[DailyCompletionRate]
    totalTasksThisWeek: int = 0
    completedTasksThisWeek: int = 0
    weeklyDensityScore: float | None = None  # 이번주 평균 밀도


class MentorInfoResponse(BaseModel):
    """담당 멘토 정보 응답"""
    mentorId: str | None = None
    mentorName: str | None = None
    avatar: int = 1
    university: str | None = None
    department: str | None = None
    subjects: list[str] = []
    recentFeedbackCount: int = 0
