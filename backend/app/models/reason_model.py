from app.utils.common import utc_now


def build_reason_document(user_id: str, emotion_id: str, text: str) -> dict:
    return {
        "user_id": user_id,
        "emotion_id": emotion_id,
        "text": text,
        "created_at": utc_now(),
    }
