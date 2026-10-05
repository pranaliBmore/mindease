from fastapi import UploadFile

from app.schemas.auth_schema import LoginRequest, SignupRequest, UpdateProfileRequest
from app.services.auth_service import AuthService

auth_service = AuthService()


async def signup_controller(payload: SignupRequest) -> dict:
    return await auth_service.signup(payload)


async def login_controller(payload: LoginRequest) -> dict:
    return await auth_service.login(payload)


async def logout_controller(user: dict) -> dict:
    return await auth_service.logout(user)


async def me_controller(user: dict) -> dict:
    return await auth_service.profile(user)


async def verify_email_controller(user: dict, otp: str) -> dict:
    return await auth_service.verify_email(user, otp)


async def resend_otp_controller(user: dict) -> dict:
    return await auth_service.resend_otp(user)


async def update_profile_controller(user: dict, payload: UpdateProfileRequest) -> dict:
    return await auth_service.update_profile(user, payload.name, payload.bio)


async def upload_avatar_controller(user: dict, file: UploadFile) -> dict:
    return await auth_service.upload_avatar(user, file)
