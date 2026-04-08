from app.utils.common import utc_now


def build_community_document(name: str) -> dict:
    return {
        "name": name.lower(),
        "members": [],
        "created_at": utc_now(),
    }
