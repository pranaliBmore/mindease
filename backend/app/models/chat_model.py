from app.utils.common import utc_now


def build_chat_message_document(
    user_id: str, user_message: str, ai_reply: str, provider_used: str, detected_emotion: str | None = None
) -> dict:
    return {
        "user_id": user_id,
        "user_message": user_message,
        "ai_reply": ai_reply,
        "provider_used": provider_used,
        "detected_emotion": detected_emotion or "neutrality",
        "created_at": utc_now(),
    }
