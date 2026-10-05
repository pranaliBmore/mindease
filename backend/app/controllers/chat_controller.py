from app.services.chat_service import ChatService

chat_service = ChatService()


async def send_chat_controller(
    user: dict, message: str, emotion_context: str | None, mode: str = "chat"
) -> dict:
    return await chat_service.send_message(
        user=user, message=message, emotion_context=emotion_context, mode=mode
    )


async def chat_history_controller(user: dict) -> dict:
    return await chat_service.history(user)


async def clear_chat_controller(user: dict) -> dict:
    return await chat_service.clear(user)
