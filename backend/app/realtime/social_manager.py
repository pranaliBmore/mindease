import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SocialConnectionManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._user_to_ws: dict[str, set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._user_to_ws.setdefault(user_id, set()).add(websocket)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            bucket = self._user_to_ws.get(user_id)
            if not bucket:
                return
            bucket.discard(websocket)
            if not bucket:
                del self._user_to_ws[user_id]

    async def send_to_user(self, user_id: str, payload: dict) -> None:
        async with self._lock:
            targets = list(self._user_to_ws.get(user_id, set()))
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception as exc:  # noqa: BLE001
                logger.debug("WS send failed, dropping socket: %s", exc)
                await self.disconnect(user_id, ws)


social_manager = SocialConnectionManager()
