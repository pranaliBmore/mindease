import json
import logging
from typing import Any

from app.ai.providers import AIProviderService
from app.services.chat_fallback import generate_support_reply
from app.services.intent import classify_intent
from app.services.local_nlp import classify_emotion_vader

logger = logging.getLogger(__name__)


class AIEngine:
    def __init__(self) -> None:
        self.providers = AIProviderService()

    async def respond(
        self,
        *,
        user_message: str,
        conversation_history: str,
        emotion_hint: str | None = None,
        context_tag: str = "chat",
    ) -> dict[str, Any]:
        msg = (user_message or "").strip()
        if not msg:
            return {
                "message": "I’m here with you. Could you type a little more about what’s going on so I can help better?",
                "provider_used": "local",
                "intent": "empty",
                "detected_emotion": "neutrality",
            }

        intent = classify_intent(msg)
        local_emotion = classify_emotion_vader(msg)
        emotion = local_emotion.emotion

        prompt = (
            "You are MindEase, a supportive assistant for anxiety and confidence building.\n"
            "Your goals:\n"
            "- Respond empathetically and practically.\n"
            "- If the user asks a question, answer clearly.\n"
            "- If the user is unclear, ask one gentle follow-up question.\n"
            "- Avoid repetition and robotic phrasing.\n"
            "- Keep it non-clinical and safe.\n"
            f"\nContext: {context_tag}\n"
            f"Detected emotion (best effort): {emotion}\n"
            f"Intent (best effort): {intent.intent}\n"
            f"Recent conversation:\n{conversation_history}\n"
            f"User: {msg}\n"
            "Assistant:"
        )

        reply, provider = await self.providers.generate_response(prompt)
        reply = (reply or "").strip()
        if not reply or provider == "fallback":
            reply = generate_support_reply(msg, emotion_hint)
            provider = "local"

        return {
            "message": reply,
            "provider_used": provider,
            "intent": intent.intent,
            "detected_emotion": emotion,
        }


ai_engine = AIEngine()

