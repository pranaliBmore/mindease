from app.schemas.match_schema import MatchStartRequest
from app.services.match_service import match_service


async def match_start_controller(user: dict, payload: MatchStartRequest) -> dict:
    return await match_service.start(user, payload.model_dump())


async def match_state_controller(user: dict) -> dict:
    return await match_service.state(user)


async def match_cancel_controller(user: dict) -> dict:
    return await match_service.cancel(user)


async def match_messages_controller(user: dict, session_id: str, limit: int) -> list[dict]:
    return await match_service.list_messages(user, session_id, limit)


async def match_reveal_controller(user: dict, session_id: str) -> dict:
    return await match_service.reveal(user, session_id)


async def match_end_controller(user: dict, session_id: str) -> dict:
    return await match_service.end(user, session_id)


async def match_report_controller(user: dict, session_id: str, reason: str) -> dict:
    return await match_service.report(user, session_id, reason)
