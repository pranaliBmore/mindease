from fastapi import UploadFile

from app.schemas.emotion_schema import AttachReasonRequest
from app.services.emotion_service import EmotionService

emotion_service = EmotionService()


async def detect_emotion_controller(
    user: dict, image_base64: str | None, image_file: UploadFile | None, reason: str | None
) -> dict:
    return await emotion_service.detect_and_store(user, image_base64=image_base64, image_file=image_file, reason=reason)


async def emotion_history_controller(user: dict) -> list[dict]:
    return await emotion_service.history(user)


async def attach_reason_controller(user: dict, payload: AttachReasonRequest) -> dict:
    return await emotion_service.attach_reason(user, payload.emotion_id, payload.text)
