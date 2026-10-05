import logging
from datetime import timedelta, timezone
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile, status

from app.config.database import db
from app.config.settings import get_settings
from app.models.user_model import build_user_document
from app.schemas.auth_schema import LoginRequest, SignupRequest
from app.services.email_service import generate_otp, send_otp_email
from app.utils.common import serialize_mongo_id, to_object_id, utc_now
from app.utils.security import create_access_token, create_refresh_token, hash_password, verify_password

logger = logging.getLogger(__name__)
settings = get_settings()

_HIDDEN_FIELDS = ("password_hash", "token_version", "otp_hash", "otp_expires_at", "otp_attempts")
_ALLOWED_AVATAR_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


class AuthService:
    async def signup(self, payload: SignupRequest, background_tasks: BackgroundTasks) -> dict:
        existing = await db.users.find_one({"email": payload.email.lower()})
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

        user_doc = build_user_document(
            name=payload.name.strip(),
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
        )
        insert_result = await db.users.insert_one(user_doc)
        user_id = str(insert_result.inserted_id)

        # The OTP is generated and stored synchronously (fast, DB-only); the actual
        # email send runs after the response goes out. SMTP over the public internet
        # (especially from a cloud host to Gmail) can be slow or occasionally stall,
        # and signup must never hang waiting on it.
        await self._issue_otp(background_tasks, user_id, payload.email.lower(), payload.name.strip())

        return {
            "access_token": create_access_token(user_id, token_version=0),
            "refresh_token": create_refresh_token(user_id),
            "token_type": "bearer",
        }

    async def login(self, payload: LoginRequest) -> dict:
        user = await db.users.find_one({"email": payload.email.lower()})
        stored_hash = user.get("password_hash") if user else None
        if not user or not stored_hash or not verify_password(payload.password, stored_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        user_id = str(user["_id"])
        tv = int(user.get("token_version", 0))
        return {
            "access_token": create_access_token(user_id, token_version=tv),
            "refresh_token": create_refresh_token(user_id),
            "token_type": "bearer",
        }

    async def logout(self, user: dict) -> dict:
        await db.users.update_one({"_id": user["_id"]}, {"$inc": {"token_version": 1}})
        return {"message": "Logged out successfully"}

    async def profile(self, user: dict) -> dict:
        safe = {k: v for k, v in user.items() if k not in _HIDDEN_FIELDS}
        return serialize_mongo_id(safe)

    # --- Email verification (OTP) -------------------------------------------------

    async def _issue_otp(
        self, background_tasks: BackgroundTasks, user_id: str, email: str, name: str,
    ) -> None:
        otp = generate_otp()
        await db.users.update_one(
            {"_id": to_object_id(user_id)},
            {
                "$set": {
                    "otp_hash": hash_password(otp),
                    "otp_expires_at": utc_now() + timedelta(minutes=settings.otp_expire_minutes),
                    "otp_attempts": 0,
                },
            },
        )
        background_tasks.add_task(self._send_otp_background, email, name, otp)

    async def _send_otp_background(self, email: str, name: str, otp: str) -> None:
        try:
            await send_otp_email(email, name, otp)
        except HTTPException as exc:
            # Runs after the HTTP response is already sent - nowhere to surface this
            # but the log. The user can hit "Resend code" if it never arrives.
            logger.warning("Background OTP email send failed for %s: %s", email, exc.detail)

    async def resend_otp(self, user: dict, background_tasks: BackgroundTasks) -> dict:
        if user.get("email_verified"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified")
        await self._issue_otp(background_tasks, str(user["_id"]), user["email"], user.get("name", ""))
        return {"message": f"A new verification code was sent to {user['email']}"}

    async def verify_email(self, user: dict, otp: str) -> dict:
        if user.get("email_verified"):
            return {"message": "Email already verified"}

        otp_hash = user.get("otp_hash")
        expires_at = user.get("otp_expires_at")
        attempts = int(user.get("otp_attempts", 0))

        if not otp_hash or not expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No verification code is pending. Request a new one.",
            )
        if attempts >= settings.otp_max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many incorrect attempts. Request a new code.",
            )
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if utc_now() > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This code expired. Request a new one.",
            )

        if not verify_password(otp.strip(), otp_hash):
            remaining = settings.otp_max_attempts - (attempts + 1)
            await db.users.update_one({"_id": user["_id"]}, {"$inc": {"otp_attempts": 1}})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Incorrect code. {max(remaining, 0)} attempt(s) left.",
            )

        await db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {"email_verified": True, "otp_hash": None, "otp_expires_at": None, "otp_attempts": 0},
            },
        )
        return {"message": "Email verified"}

    # --- Profile --------------------------------------------------------------

    async def update_profile(self, user: dict, name: str | None, bio: str | None) -> dict:
        updates: dict = {}
        if name is not None and name.strip():
            updates["name"] = name.strip()
        if bio is not None:
            updates["bio"] = bio.strip()
        if updates:
            await db.users.update_one({"_id": user["_id"]}, {"$set": updates})
            user = await db.users.find_one({"_id": user["_id"]})
        return await self.profile(user)

    async def upload_avatar(self, user: dict, file: UploadFile) -> dict:
        ext = _ALLOWED_AVATAR_TYPES.get(file.content_type or "")
        if not ext:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPEG, PNG, or WebP images are allowed.",
            )
        content = await file.read()
        if len(content) > settings.avatar_max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image must be under {settings.avatar_max_bytes // (1024 * 1024)}MB.",
            )

        user_id = str(user["_id"])
        upload_dir = Path(settings.avatar_upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        for stale in upload_dir.glob(f"{user_id}.*"):
            stale.unlink(missing_ok=True)

        dest = upload_dir / f"{user_id}{ext}"
        dest.write_bytes(content)

        avatar_url = f"/uploads/avatars/{user_id}{ext}?v={int(utc_now().timestamp())}"
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"avatar_url": avatar_url}})
        return {"avatar_url": avatar_url}
