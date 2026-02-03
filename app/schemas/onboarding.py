from pydantic import BaseModel, Field


class MenteeOnboardingRequest(BaseModel):
    grade: str = Field(
        pattern="^(HIGH1|HIGH2|HIGH3|N_REPEAT)$",
        examples=["HIGH2"],
        description="학년 (HIGH1, HIGH2, HIGH3, N_REPEAT)",
    )
    subjects: list[str] = Field(
        min_length=1,
        examples=[["KOREAN", "MATH"]],
        description="수강 과목 목록 (KOREAN, ENGLISH, MATH)",
    )
    currentGrades: dict[str, int] = Field(
        examples=[{"KOREAN": 3, "ENGLISH": 2, "MATH": 4}],
        description="현재 과목별 등급 (1~9)",
    )
    targetGrades: dict[str, int] = Field(
        examples=[{"KOREAN": 1, "ENGLISH": 1, "MATH": 2}],
        description="목표 과목별 등급 (1~9)",
    )


class MentorOnboardingRequest(BaseModel):
    university: str = Field(
        min_length=1, max_length=100, examples=["서울대학교"]
    )
    department: str = Field(
        min_length=1, max_length=100, examples=["컴퓨터공학부"]
    )
    subjects: list[str] = Field(
        min_length=1,
        examples=[["KOREAN", "ENGLISH"]],
        description="코칭 가능 과목 (KOREAN, ENGLISH, MATH)",
    )
    coachingExperience: bool = Field(
        default=False,
        examples=[True],
        description="코칭 경험 여부",
    )


class ParentOnboardingRequest(BaseModel):
    inviteCode: str = Field(
        min_length=1,
        examples=["550e8400-e29b-41d4-a716-446655440000"],
        description="멘티(자녀)의 초대 코드",
    )


class MenteeProfileResponse(BaseModel):
    id: str
    grade: str
    subjects: list[str]
    currentGrades: dict
    targetGrades: dict
    onboardingDone: bool
    inviteCode: str

    model_config = {"from_attributes": True}


class MentorProfileResponse(BaseModel):
    id: str
    university: str
    department: str
    subjects: list[str]
    coachingExperience: bool
    onboardingDone: bool

    model_config = {"from_attributes": True}


class ParentProfileResponse(BaseModel):
    id: str
    menteeId: str

    model_config = {"from_attributes": True}
