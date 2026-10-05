from app.utils.common import utc_now


def build_queue_document(user_id: str, answers: dict) -> dict:
    return {
        "user_id": user_id,
        "answers": answers,
        "status": "waiting",
        "created_at": utc_now(),
    }


def build_session_document(
    user_a: str,
    user_b: str,
    alias_a: str,
    alias_b: str,
    answers_a: dict,
    answers_b: dict,
    score: int,
) -> dict:
    return {
        "user_a": user_a,
        "user_b": user_b,
        "alias_a": alias_a,
        "alias_b": alias_b,
        "answers_a": answers_a,
        "answers_b": answers_b,
        "score": score,
        "status": "active",
        "created_at": utc_now(),
        "ended_at": None,
        "end_reason": None,
    }
