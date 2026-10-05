from fastapi import APIRouter, Depends

from app.controllers.chat_controller import (
    chat_history_controller,
    clear_chat_controller,
    send_chat_controller,
)
from app.middleware.auth_middleware import get_current_user
from app.schemas.chat_schema import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    GenericMessageResponse,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/send", response_model=ChatResponse)
async def send_chat(payload: ChatRequest, current_user: dict = Depends(get_current_user)):
    return await send_chat_controller(
        current_user, payload.message, payload.emotion_context, payload.mode
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def chat_history(current_user: dict = Depends(get_current_user)):
    return await chat_history_controller(current_user)


@router.post("/clear", response_model=GenericMessageResponse)
async def clear_chat(current_user: dict = Depends(get_current_user)):
    return await clear_chat_controller(current_user)
