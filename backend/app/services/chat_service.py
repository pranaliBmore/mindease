from app.config.database import db
from app.models.chat_model import build_chat_message_document
from app.services.ai_engine import ai_engine


class ChatService:
    def __init__(self) -> None:
        pass

    async def send_message(self, user: dict, message: str, emotion_context: str | None) -> dict:
        history_docs = (
            await db.chat_messages.find({"user_id": str(user["_id"])}).sort("created_at", -1).limit(6).to_list(length=6)
        )
        history_docs.reverse()
        history_text = "\n".join(
            [f"User: {item['user_message']}\nAssistant: {item['ai_reply']}" for item in history_docs]
        )
        emotion_line = emotion_context or "unknown"
        engine_out = await ai_engine.respond(
            user_message=message,
            conversation_history=history_text,
            emotion_hint=emotion_context,
            context_tag="ai_chat",
        )
        reply = engine_out["message"]
        provider = engine_out["provider_used"]
        chat_doc = build_chat_message_document(
            user_id=str(user["_id"]), user_message=message, ai_reply=reply, provider_used=provider
        )
        await db.chat_messages.insert_one(chat_doc)
        return {
            "reply": reply,
            "provider_used": provider,
            "intent": engine_out.get("intent"),
            "detected_emotion": engine_out.get("detected_emotion"),
        }
