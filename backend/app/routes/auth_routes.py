from fastapi import APIRouter, Depends, Request

from app.controllers.auth_controller import login_controller, logout_controller, me_controller, signup_controller
from app.config.settings import get_settings
from app.middleware.auth_middleware import get_current_user
from app.middleware.rate_limit import limiter
from app.schemas.auth_schema import LoginRequest, LogoutResponse, SignupRequest, TokenResponse
from app.schemas.user_schema import UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
_AUTH_LIMIT = f"{get_settings().rate_limit_auth_per_minute}/minute"


@router.post("/signup", response_model=TokenResponse)
@limiter.limit(_AUTH_LIMIT)
async def signup(request: Request, payload: SignupRequest):  # noqa: ARG001 - request required by slowapi
    return await signup_controller(payload)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(_AUTH_LIMIT)
async def login(request: Request, payload: LoginRequest):  # noqa: ARG001 - request required by slowapi
    return await login_controller(payload)


@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    return await logout_controller(current_user)


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return await me_controller(current_user)
