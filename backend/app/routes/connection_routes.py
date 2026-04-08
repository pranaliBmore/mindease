from fastapi import APIRouter, Depends, Query

from app.controllers.connection_controller import (
    accept_connection_controller,
    connection_state_controller,
    list_dm_controller,
    reject_connection_controller,
    search_users_controller,
    send_connection_request_controller,
)
from app.middleware.auth_middleware import get_current_user
from app.schemas.community_schema import (
    ConnectionRequest,
    ConnectionRequestIdBody,
    GenericMessageResponse,
)

router = APIRouter(prefix="/api/connection", tags=["connection"])


@router.post("/request", response_model=GenericMessageResponse)
async def send_connection_request(
    payload: ConnectionRequest,
    current_user: dict = Depends(get_current_user),
):
    return await send_connection_request_controller(
        current_user,
        payload.target_user_email,
        payload.target_user_id,
    )


@router.post("/add", response_model=GenericMessageResponse)
async def add_connection_legacy(
    payload: ConnectionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Deprecated alias: sends a connection request (recipient must accept)."""
    return await send_connection_request_controller(
        current_user,
        payload.target_user_email,
        payload.target_user_id,
    )


@router.get("/state", response_model=None)
async def connection_state(current_user: dict = Depends(get_current_user)):
    return await connection_state_controller(current_user)


@router.post("/accept", response_model=GenericMessageResponse)
async def accept_connection(
    payload: ConnectionRequestIdBody,
    current_user: dict = Depends(get_current_user),
):
    return await accept_connection_controller(current_user, payload.request_id)


@router.post("/reject", response_model=GenericMessageResponse)
async def reject_connection(
    payload: ConnectionRequestIdBody,
    current_user: dict = Depends(get_current_user),
):
    return await reject_connection_controller(current_user, payload.request_id)


@router.get("/users/search", response_model=None)
async def search_connection_users(
    q: str = Query(..., min_length=2, max_length=80),
    current_user: dict = Depends(get_current_user),
):
    return await search_users_controller(current_user, q)


@router.get("/messages/{peer_user_id}", response_model=None)
async def list_direct_messages(
    peer_user_id: str,
    limit: int = Query(80, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    return await list_dm_controller(current_user, peer_user_id, limit)
