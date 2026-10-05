from app.utils.common import utc_now


def build_user_document(name: str, email: str, password_hash: str) -> dict:
    return {
        "name": name,
        "email": email.lower(),
        "password_hash": password_hash,
        "avatar_url": None,
        "bio": "",
        "email_verified": False,
        "otp_hash": None,
        "otp_expires_at": None,
        "otp_attempts": 0,
        "emotional_history": [],
        "feedback_history": [],
        "communities": [],
        "connections": [],
        "token_version": 0,
        "created_at": utc_now(),
    }
