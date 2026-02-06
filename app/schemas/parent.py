from pydantic import BaseModel, Field


class MentorBasicInfo(BaseModel):
    """멘토 기본 정보 (학부모용)"""
    id: str = Field(description="멘토 프로필 ID")
    name: str = Field(description="멘토 이름")
    avatar: int = Field(default=1, description="아바타 번호 (1~20, 프론트에서 role+avatar로 이미지 조합)")
    university: str = Field(description="대학교명")
    department: str = Field(description="학과명")


class ParentDashboardResponse(BaseModel):
    """학부모 대시보드 응답"""
    # 자녀 정보
    menteeName: str = Field(description="자녀 이름")
    menteeGrade: str | None = Field(default=None, description="자녀 학년 (예: '고1')")
    menteeSubjects: list[str] = Field(default=[], description="자녀 수강 과목 목록")

    # 오늘 학습 현황
    todayTaskCount: int = Field(default=0, description="오늘 전체 과제 수")
    todayCompletedCount: int = Field(default=0, description="오늘 완료한 과제 수")
    todayCompletionRate: float = Field(default=0.0, description="오늘 과제 완수율 (0~1, 예: 0.75 = 75%)")

    # 이번주 학습 밀도
    weeklyDensityScore: float | None = Field(default=None, description="이번주 평균 학습 밀도 점수 (0~100)")

    # 멘토 정보
    mentor: MentorBasicInfo | None = Field(default=None, description="담당 멘토 정보 (없으면 null)")

    # 최근 피드백
    recentFeedbackCount: int = Field(default=0, description="최근 7일간 받은 피드백 수")


class DailyCompletionRate(BaseModel):
    """일별 완수율"""
    date: str = Field(description="날짜 (YYYY-MM-DD)")
    total: int = Field(description="해당일 전체 과제 수")
    completed: int = Field(description="해당일 완료한 과제 수")
    rate: float = Field(description="완수율 (0~1)")


class MenteeStatusResponse(BaseModel):
    """자녀 학습 현황 응답"""
    weeklyCompletionRates: list[DailyCompletionRate] = Field(description="이번주 일별 완수율 (월~일)")
    totalTasksThisWeek: int = Field(default=0, description="이번주 전체 과제 수")
    completedTasksThisWeek: int = Field(default=0, description="이번주 완료한 과제 수")
    weeklyDensityScore: float | None = Field(default=None, description="이번주 평균 학습 밀도 점수 (0~100)")


class MentorInfoResponse(BaseModel):
    """담당 멘토 정보 응답"""
    mentorId: str | None = Field(default=None, description="멘토 프로필 ID")
    mentorName: str | None = Field(default=None, description="멘토 이름")
    avatar: int = Field(default=1, description="아바타 번호 (1~20)")
    university: str | None = Field(default=None, description="대학교명")
    department: str | None = Field(default=None, description="학과명")
    subjects: list[str] = Field(default=[], description="멘토 담당 과목 목록")
    recentFeedbackCount: int = Field(default=0, description="최근 7일간 작성한 피드백 수")
