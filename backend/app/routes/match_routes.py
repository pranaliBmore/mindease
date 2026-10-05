from fastapi import APIRouter, Depends, Query

from app.controllers.match_controller import (
    match_cancel_controller,
    match_end_controller,
    match_messages_controller,
    match_report_controller,
    match_reveal_controller,
    match_start_controller,
    match_state_controller,
)
from app.middleware.auth_middleware import get_current_user
from app.schemas.community_schema import GenericMessageResponse
from app.schemas.match_schema import MatchReportRequest, MatchSessionIdBody, MatchStartRequest

router = APIRouter(prefix="/api/match", tags=["match"])


@router.post("/start", response_model=None)
async def match_start(payload: MatchStartRequest, current_user: dict = Depends(get_current_user)):
    return await match_start_controller(current_user, payload)


@router.get("/state", response_model=None)
async def match_state(current_user: dict = Depends(get_current_user)):
    return await match_state_controller(current_user)


@router.post("/cancel", response_model=GenericMessageResponse)
async def match_cancel(current_user: dict = Depends(get_current_user)):
    return await match_cancel_controller(current_user)


@router.get("/messages/{session_id}", response_model=None)
async def match_messages(
    session_id: str,
    limit: int = Query(100, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    return await match_messages_controller(current_user, session_id, limit)


@router.post("/reveal", response_model=GenericMessageResponse)
async def match_reveal(payload: MatchSessionIdBody, current_user: dict = Depends(get_current_user)):
    return await match_reveal_controller(current_user, payload.session_id)


@router.post("/end", response_model=GenericMessageResponse)
async def match_end(payload: MatchSessionIdBody, current_user: dict = Depends(get_current_user)):
    return await match_end_controller(current_user, payload.session_id)


@router.post("/report", response_model=GenericMessageResponse)
async def match_report(payload: MatchReportRequest, current_user: dict = Depends(get_current_user)):
    return await match_report_controller(current_user, payload.session_id, payload.reason)
