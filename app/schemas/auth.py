from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    loginId: str = Field(
        min_length=4, max_length=20,
        pattern="^[a-zA-Z0-9_]+$",
        examples=["student01"],
    )
    password: str = Field(min_length=8, max_length=100, examples=["mypassword123"])
    name: str = Field(min_length=1, max_length=50, examples=["홍길동"])
    phone: str = Field(min_length=1, max_length=20, examples=["01012345678"])
    role: str = Field(pattern="^(MENTEE|MENTOR|PARENT)$", examples=["MENTEE"])


class LoginRequest(BaseModel):
    loginId: str = Field(examples=["student01"])
    password: str = Field(examples=["mypassword123"])


class UserResponse(BaseModel):
    id: str
    loginId: str
    role: str
    name: str
    phone: str | None = None
    profileImage: str | None = None
    nickname: str | None = None

    model_config = {"from_attributes": True}


class AuthTokens(BaseModel):
    accessToken: str
    refreshToken: str


class AuthResponse(BaseModel):
    user: UserResponse
    accessToken: str
    refreshToken: str


class MeResponse(BaseModel):
    user: UserResponse
    profile: dict | None = None
