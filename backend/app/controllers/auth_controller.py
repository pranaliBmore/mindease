from app.schemas.auth_schema import LoginRequest, SignupRequest
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
