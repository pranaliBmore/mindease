from app.services.chat_service import ChatService

chat_service = ChatService()


async def send_chat_controller(user: dict, message: str, emotion_context: str | None) -> dict:
    return await chat_service.send_message(user=user, message=message, emotion_context=emotion_context)
