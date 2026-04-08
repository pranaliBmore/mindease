from fastapi import APIRouter, Depends

from app.controllers.chat_controller import send_chat_controller
from app.middleware.auth_middleware import get_current_user
from app.schemas.chat_schema import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/send", response_model=ChatResponse)
async def send_chat(payload: ChatRequest, current_user: dict = Depends(get_current_user)):
    return await send_chat_controller(current_user, payload.message, payload.emotion_context)
