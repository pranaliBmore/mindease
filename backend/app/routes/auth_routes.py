from fastapi import APIRouter, Depends

from app.controllers.auth_controller import login_controller, logout_controller, me_controller, signup_controller
from app.middleware.auth_middleware import get_current_user
from app.schemas.auth_schema import LoginRequest, LogoutResponse, SignupRequest, TokenResponse
from app.schemas.user_schema import UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
async def signup(payload: SignupRequest):
    return await signup_controller(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    return await login_controller(payload)


@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user: dict = Depends(get_current_user)):
    return await logout_controller(current_user)


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return await me_controller(current_user)
