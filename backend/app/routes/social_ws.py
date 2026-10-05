import logging

from fastapi import APIRouter, HTTPException, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.realtime.social_manager import social_manager
from app.services.ai_engine import CRISIS_SUPPORT_MESSAGE, check_crisis
from app.services.match_service import match_service
from app.services.social_service import social_service
from app.utils.ws_auth import get_user_from_access_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/social")
async def social_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    token = websocket.query_params.get("token")
    user = await get_user_from_access_token(token)
    if not user:
        await websocket.close(code=4401)
        return

    uid = str(user["_id"])
    await social_manager.connect(uid, websocket)
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except Exception:  # noqa: BLE001
                try:
                    await websocket.send_json({"type": "error", "detail": "Expected a JSON object"})
                except Exception:  # noqa: BLE001
                    break
                continue

            msg_type = data.get("type") if isinstance(data, dict) else None
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if msg_type == "dm":
                to_uid = data.get("to_user_id")
                text = data.get("text", "")
                if not isinstance(to_uid, str) or not isinstance(text, str):
                    await websocket.send_json({"type": "error", "detail": "Invalid payload"})
                    continue
                try:
                    msg = await social_service.create_dm(user, to_uid, text)
                    payload = {"type": "dm", "message": msg}
                    await social_manager.send_to_user(to_uid, payload)
                    await social_manager.send_to_user(uid, payload)
                except HTTPException as exc:
                    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
                    await websocket.send_json({"type": "error", "detail": detail})
                continue
            if msg_type == "match_message":
                session_id = data.get("session_id")
                text = data.get("text", "")
                if not isinstance(session_id, str) or not isinstance(text, str):
                    await websocket.send_json({"type": "error", "detail": "Invalid payload"})
                    continue
                try:
                    result = await match_service.send_message(user, session_id, text)
                    msg = result["message"]
                    peer_uid = result["peer_user_id"]
                    payload = {"type": "match_message", "message": msg}
                    await social_manager.send_to_user(peer_uid, payload)
                    await social_manager.send_to_user(uid, payload)
                    if check_crisis(text):
                        await social_manager.send_to_user(
                            uid, {"type": "match_safety", "detail": CRISIS_SUPPORT_MESSAGE},
                        )
                except HTTPException as exc:
                    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
                    await websocket.send_json({"type": "error", "detail": detail})
                continue
            await websocket.send_json({"type": "error", "detail": "Unknown message type"})
    finally:
        await social_manager.disconnect(uid, websocket)
