from app.utils.common import utc_now


def build_feedback_document(
    user_id: str, flow_type: str, content_type: str | None, message: str, rating: int
) -> dict:
    return {
        "user_id": user_id,
        "flow_type": flow_type,
        "content_type": content_type,
        "message": message,
        "rating": rating,
        "created_at": utc_now(),
    }
