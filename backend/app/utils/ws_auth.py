from jose import JWTError, jwt

from app.config.database import db
from app.config.settings import get_settings
from app.utils.common import to_object_id

settings = get_settings()


async def get_user_from_access_token(token: str | None) -> dict | None:
    if not token or not str(token).strip():
        return None
    try:
        payload = jwt.decode(str(token).strip(), settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        token_tv = int(payload.get("tv", 0))
    except JWTError:
        return None
    user = await db.users.find_one({"_id": to_object_id(user_id)})
    if not user:
        return None
    if int(user.get("token_version", 0)) != token_tv:
        return None
    return user
