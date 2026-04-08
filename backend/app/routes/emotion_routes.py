from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from app.controllers.emotion_controller import (
    attach_reason_controller,
    detect_emotion_controller,
    emotion_history_controller,
)
from app.middleware.auth_middleware import get_current_user
from app.schemas.emotion_schema import (
    AttachReasonRequest,
    AttachReasonResponse,
    EmotionHistoryItem,
    EmotionResponse,
)

router = APIRouter(prefix="/api/emotion", tags=["emotion"])


@router.post("/detect", response_model=EmotionResponse)
async def detect_emotion(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    content_type = (request.headers.get("content-type") or "").lower()
    image_file: UploadFile | None = None
    image_base64: str | None = None
    reason: str | None = None

    if "multipart/form-data" in content_type:
        form_data = await request.form()
        candidate_file = form_data.get("image_file")
        image_file = candidate_file if isinstance(candidate_file, UploadFile) else None
        image_base64 = form_data.get("image_base64")
        reason = form_data.get("reason")
    elif "application/json" in content_type:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")
        image_base64 = payload.get("image_base64")
        reason = payload.get("reason")
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Use multipart/form-data (image_file) or application/json (image_base64).",
        )

    return await detect_emotion_controller(
        user=current_user,
        image_base64=image_base64,
        image_file=image_file,
        reason=reason,
    )


@router.get("/history", response_model=list[EmotionHistoryItem])
async def emotion_history(current_user: dict = Depends(get_current_user)):
    return await emotion_history_controller(current_user)


@router.post("/attach-reason", response_model=AttachReasonResponse)
async def attach_emotion_reason(payload: AttachReasonRequest, current_user: dict = Depends(get_current_user)):
    return await attach_reason_controller(current_user, payload)
