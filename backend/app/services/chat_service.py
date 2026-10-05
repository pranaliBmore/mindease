from app.config.database import db
from app.models.chat_model import build_chat_message_document
from app.services.ai_engine import ai_engine
from app.utils.common import serialize_mongo_id
from app.utils.crypto import decrypt_text, encrypt_text

_HISTORY_LIMIT = 50


class ChatService:
    async def send_message(
        self, user: dict, message: str, emotion_context: str | None, mode: str = "chat"
    ) -> dict:
        history_docs = (
            await db.chat_messages.find({"user_id": str(user["_id"])}).sort("created_at", -1).limit(6).to_list(length=6)
        )
        history_docs.reverse()
        history_text = "\n".join(
            f"Person: {decrypt_text(item['user_message'])}\nMindEase: {decrypt_text(item['ai_reply'])}"
            for item in history_docs
        )
        engine_out = await ai_engine.respond(
            user_message=message,
            conversation_history=history_text,
            emotion_hint=emotion_context,
            context_tag="ai_chat",
            mode=mode or "chat",
        )
        reply = engine_out["message"]
        provider = engine_out["provider_used"]
        chat_doc = build_chat_message_document(
            user_id=str(user["_id"]),
            user_message=encrypt_text(message),
            ai_reply=encrypt_text(reply),
            provider_used=provider,
        )
        await db.chat_messages.insert_one(chat_doc)
        return {
            "reply": reply,
            "provider_used": provider,
            "intent": engine_out.get("intent"),
            "detected_emotion": engine_out.get("detected_emotion"),
            "safety": engine_out.get("safety"),
        }

    async def history(self, user: dict) -> dict:
        rows = (
            await db.chat_messages.find({"user_id": str(user["_id"])})
            .sort("created_at", 1)
            .limit(_HISTORY_LIMIT)
            .to_list(length=_HISTORY_LIMIT)
        )
        messages = []
        for r in rows:
            r = serialize_mongo_id(dict(r))
            r["user_message"] = decrypt_text(r.get("user_message", ""))
            r["ai_reply"] = decrypt_text(r.get("ai_reply", ""))
            messages.append(r)
        return {"messages": messages}

    async def clear(self, user: dict) -> dict:
        result = await db.chat_messages.delete_many({"user_id": str(user["_id"])})
        return {"message": f"Cleared {result.deleted_count} messages"}
