from app.utils.common import utc_now


def build_user_document(name: str, email: str, password_hash: str) -> dict:
    return {
        "name": name,
        "email": email.lower(),
        "password_hash": password_hash,
        "emotional_history": [],
        "feedback_history": [],
        "communities": [],
        "connections": [],
        "token_version": 0,
        "created_at": utc_now(),
    }
