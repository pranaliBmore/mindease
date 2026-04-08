from fastapi import HTTPException, status

from app.config.database import db
from app.models.user_model import build_user_document
from app.schemas.auth_schema import LoginRequest, SignupRequest
from app.utils.common import serialize_mongo_id
from app.utils.security import create_access_token, create_refresh_token, hash_password, verify_password


class AuthService:
    async def signup(self, payload: SignupRequest) -> dict:
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
        safe = {k: v for k, v in user.items() if k not in ("password_hash", "token_version")}
        return serialize_mongo_id(safe)
