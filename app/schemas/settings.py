from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    id: str
    loginId: str
    name: str
    phone: str | None = None
    profileImage: str | None = None
    nickname: str | None = None
    role: str

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    phone: str | None = None
    nickname: str | None = Field(default=None, max_length=30)
    profileImage: str | None = None


class MenteeSettingsRequest(BaseModel):
    targetGrades: dict | None = Field(
        default=None, examples=[{"KOREAN": 1, "ENGLISH": 1, "MATH": 2}]
    )
    subjects: list[str] | None = Field(
        default=None, examples=[["KOREAN", "MATH"]]
    )


class MentorSettingsRequest(BaseModel):
    subjects: list[str] | None = Field(
        default=None, examples=[["KOREAN", "ENGLISH"]]
    )
