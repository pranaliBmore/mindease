from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile

from app.controllers.auth_controller import (
    login_controller,
    logout_controller,
    me_controller,
    resend_otp_controller,
    signup_controller,
    update_profile_controller,
    upload_avatar_controller,
    verify_email_controller,
)
from app.config.settings import get_settings
from app.middleware.auth_middleware import get_current_user
from app.middleware.rate_limit import limiter
from app.schemas.auth_schema import (
    AvatarResponse,
    LoginRequest,
    LogoutResponse,
    MessageResponse,
    SignupRequest,
    TokenResponse,
    UpdateProfileRequest,
    VerifyEmailRequest,
)
from app.schemas.user_schema import UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])
_AUTH_LIMIT = f"{get_settings().rate_limit_auth_per_minute}/minute"
_OTP_LIMIT = "5/minute"


@router.post("/signup", response_model=TokenResponse)
@limiter.limit(_AUTH_LIMIT)
async def signup(request: Request, payload: SignupRequest, background_tasks: BackgroundTasks):  # noqa: ARG001
    return await signup_controller(payload, background_tasks)


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


@router.post("/verify-email", response_model=MessageResponse)
@limiter.limit(_OTP_LIMIT)
async def verify_email(
    request: Request,  # noqa: ARG001 - request required by slowapi
    payload: VerifyEmailRequest,
    current_user: dict = Depends(get_current_user),
):
    return await verify_email_controller(current_user, payload.otp)


@router.post("/resend-otp", response_model=MessageResponse)
@limiter.limit(_OTP_LIMIT)
async def resend_otp(
    request: Request,  # noqa: ARG001 - request required by slowapi
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    return await resend_otp_controller(current_user, background_tasks)


@router.patch("/profile", response_model=UserOut)
async def update_profile(payload: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    return await update_profile_controller(current_user, payload)


@router.post("/avatar", response_model=AvatarResponse)
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    return await upload_avatar_controller(current_user, file)


# TEMPORARY DEBUG ROUTE - sends the test email synchronously (not via BackgroundTasks) so
# the real exception, if any, comes straight back in the HTTP response. Remove once the
# production SMTP issue is diagnosed.
@router.post("/debug-smtp-test", response_model=None)
async def debug_smtp_test(current_user: dict = Depends(get_current_user)):
    from app.services.email_service import send_otp_email

    try:
        await send_otp_email(current_user["email"], current_user.get("name", "Debug"), "123456")
        return {"ok": True, "message": f"Sent to {current_user['email']}"}
    except Exception as exc:  # noqa: BLE001
        real = exc.__cause__ or exc
        return {"ok": False, "error_type": type(real).__name__, "error_detail": str(real)}
