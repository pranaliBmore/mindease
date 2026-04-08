from app.utils.common import utc_now


def build_solo_analysis_document(
    *,
    user_id: str,
    session_id: str,
    text: str,
    emotion: str,
    confidence: float,
    model_used: str,
    suggestions: dict,
) -> dict:
    return {
        "user_id": user_id,
        "session_id": session_id,
        "text": text,
        "emotion": emotion,
        "confidence": float(confidence),
        "model_used": model_used,
        "suggestions": suggestions,
        "created_at": utc_now(),
    }

