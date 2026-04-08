from app.services.social_service import social_service


async def send_connection_request_controller(
    user: dict,
    target_user_email: str | None,
    target_user_id: str | None,
) -> dict:
    return await social_service.send_request(
        user,
        target_user_email=target_user_email,
        target_user_id=target_user_id,
    )


async def connection_state_controller(user: dict) -> dict:
    return await social_service.connection_state(user)


async def accept_connection_controller(user: dict, request_id: str) -> dict:
    return await social_service.accept_request(user, request_id)


async def reject_connection_controller(user: dict, request_id: str) -> dict:
    return await social_service.reject_request(user, request_id)


async def search_users_controller(user: dict, q: str) -> list[dict]:
    return await social_service.search_users(user, q)


async def list_dm_controller(user: dict, peer_user_id: str, limit: int) -> list[dict]:
    return await social_service.list_messages(user, peer_user_id, limit)
