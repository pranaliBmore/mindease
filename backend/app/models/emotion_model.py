from app.utils.common import utc_now


def build_emotion_document(
    user_id: str,
    emotion: str,
    confidence: float,
    description: str,
    reason: str | None = None,
) -> dict:
    return {
        "user_id": user_id,
        "emotion": emotion,
        "confidence": confidence,
        "description": description,
        "reason": reason,
        "created_at": utc_now(),
    }
