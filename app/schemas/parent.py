from pydantic import BaseModel


class ParentDashboardResponse(BaseModel):
    menteeName: str
    menteeGrade: str | None = None
    menteeSubjects: list[str] = []
    todayTaskCount: int = 0
    todayCompletedCount: int = 0
    todayCompletionRate: float = 0.0
    mentorName: str | None = None
    recentFeedbackCount: int = 0


class MenteeStatusResponse(BaseModel):
    weeklyCompletionRates: list[dict]
    totalTasksThisWeek: int = 0
    completedTasksThisWeek: int = 0


class MentorInfoResponse(BaseModel):
    mentorId: str | None = None
    mentorName: str | None = None
    university: str | None = None
    department: str | None = None
    subjects: list[str] = []
    recentFeedbackCount: int = 0
