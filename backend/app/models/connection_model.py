from app.utils.common import utc_now


def build_connection_document(user_id: str, target_user_id: str) -> dict:
    return {
        "user_id": user_id,
        "target_user_id": target_user_id,
        "created_at": utc_now(),
    }
