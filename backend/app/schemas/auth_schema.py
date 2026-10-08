from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    email_verified: bool = True


class LogoutResponse(BaseModel):
    message: str


class VerifyEmailRequest(BaseModel):
    otp: str = Field(min_length=4, max_length=8)


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    bio: str | None = Field(default=None, max_length=160)


class MessageResponse(BaseModel):
    message: str


class AvatarResponse(BaseModel):
    avatar_url: str
