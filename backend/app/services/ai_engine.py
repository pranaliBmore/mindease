import logging
import re
from typing import Any

from app.ai.providers import AIProviderService
from app.services.chat_fallback import generate_support_reply
from app.services.intent import classify_intent
from app.services.local_nlp import classify_emotion_vader

logger = logging.getLogger(__name__)

# --- Chat: safety --------------------------------------------------------------

_CRISIS_RE = re.compile(
    r"\b(kill myself|killing myself|end my life|ending my life|take my (own )?life|"
    r"want to die|wanna die|don'?t want to (be alive|live|wake up)|"
    r"suicid|self[\s-]?harm|hurt(ing)? myself|cut(ting)? myself|"
    r"no reason to (live|go on)|better off (dead|without me))\b",
    re.IGNORECASE,
)

_CRISIS_REPLY = (
    "I'm really glad you told me this, and I don't want you to face it alone. "
    "I'm not able to give the help you deserve here, so please reach out to people who can right now. "
    "If you're in the US, call or text 988 (Suicide & Crisis Lifeline). "
    "Anywhere else, contact your local emergency number or a crisis line. "
    "If you can, tell someone near you how you're feeling. You matter, and this can get better."
)

# --- Chat: style + guided modes ---------------------------------------------

_CHAT_STYLE = (
    "You are MindEase, a warm and calm wellness companion.\n"
    "How to reply:\n"
    "- Keep it short: 2 to 4 sentences. Never a wall of text.\n"
    "- Use plain, everyday words. No clinical terms, no jargon.\n"
    "- Sound like a kind friend, not a therapist or a robot.\n"
    "- First gently acknowledge how they feel, then offer ONE small doable step or ONE gentle question.\n"
    "- Do not diagnose. Never say 'as an AI'. Do not use markdown headings.\n"
    "- You are not a substitute for professional care; if something sounds serious, say so kindly.\n"
)

_MODE_INSTRUCTIONS = {
    "breathing": (
        "Give one very short guided breathing exercise in about 4 simple steps "
        "(for example inhale 4, hold 4, exhale 4, hold 4, repeated a few times). "
        "Warm one-line intro, then the steps. Nothing else."
    ),
    "grounding": (
        "Walk them through the 5-4-3-2-1 grounding exercise in a short, calm way: "
        "5 things you can see, 4 you can feel, 3 you can hear, 2 you can smell, 1 you can taste. "
        "Keep it gentle and brief."
    ),
    "journal_prompt": (
        "Offer exactly one thoughtful journaling prompt, 1 to 2 sentences, and nothing else. "
        "Make it kind and open-ended."
    ),
    "reframe": (
        "Gently help turn the worry they shared into a kinder, more balanced thought. "
        "Acknowledge it is hard, then offer one softer way to look at it. 2 to 3 sentences."
    ),
    "pep_talk": (
        "Give 2 to 3 short lines of honest encouragement. Warm and believable, not cheesy. "
        "Focus on their effort and the next small step."
    ),
}


def _looks_like_crisis(text: str) -> bool:
    return bool(_CRISIS_RE.search(text or ""))


def check_crisis(text: str) -> bool:
    """Public wrapper so other features (e.g. peer matching) can reuse the same crisis detector."""
    return _looks_like_crisis(text)


CRISIS_SUPPORT_MESSAGE = _CRISIS_REPLY


class AIEngine:
    def __init__(self) -> None:
        self.providers = AIProviderService()

    def _build_chat_prompt(
        self, *, msg: str, history: str, emotion: str, intent: str, mode: str
    ) -> str:
        parts = [_CHAT_STYLE]
        if mode in _MODE_INSTRUCTIONS:
            parts.append("For this reply specifically: " + _MODE_INSTRUCTIONS[mode] + "\n")
        parts.append(f"How they seem to feel: {emotion}. What they seem to want: {intent}.\n")
        if history:
            parts.append(f"Recent conversation:\n{history}\n")
        parts.append(f"Person: {msg}\nMindEase:")
        return "\n".join(parts)

    def _build_generic_prompt(
        self, *, msg: str, history: str, emotion: str, intent: str, context_tag: str
    ) -> str:
        return (
            "You are MindEase, a supportive assistant for anxiety and confidence building.\n"
            "Your goals:\n"
            "- Respond empathetically and practically.\n"
            "- If the user asks a question, answer clearly.\n"
            "- If the user is unclear, ask one gentle follow-up question.\n"
            "- Avoid repetition and robotic phrasing.\n"
            "- Keep it non-clinical and safe.\n"
            f"\nContext: {context_tag}\n"
            f"Detected emotion (best effort): {emotion}\n"
            f"Intent (best effort): {intent}\n"
            f"Recent conversation:\n{history}\n"
            f"User: {msg}\n"
            "Assistant:"
        )

    async def respond(
        self,
        *,
        user_message: str,
        conversation_history: str,
        emotion_hint: str | None = None,
        context_tag: str = "chat",
        mode: str = "chat",
    ) -> dict[str, Any]:
        msg = (user_message or "").strip()
        is_chat = context_tag == "ai_chat"

        if not msg:
            return {
                "message": (
                    "I'm here with you. Tell me a little about what's on your mind and we'll take it slowly."
                    if is_chat
                    else "I’m here with you. Could you type a little more about what’s going on so I can help better?"
                ),
                "provider_used": "local",
                "intent": "empty",
                "detected_emotion": "neutrality",
                "safety": None,
            }

        # Safety first (chat only): never route crisis language to the model.
        if is_chat and _looks_like_crisis(msg):
            logger.info("Crisis language detected in chat; returning support message.")
            return {
                "message": _CRISIS_REPLY,
                "provider_used": "local",
                "intent": "crisis",
                "detected_emotion": "fear",
                "safety": "crisis",
            }

        intent = classify_intent(msg)
        local_emotion = classify_emotion_vader(msg)
        emotion = local_emotion.emotion

        if is_chat:
            prompt = self._build_chat_prompt(
                msg=msg, history=conversation_history, emotion=emotion, intent=intent.intent, mode=mode
            )
        else:
            prompt = self._build_generic_prompt(
                msg=msg,
                history=conversation_history,
                emotion=emotion,
                intent=intent.intent,
                context_tag=context_tag,
            )

        reply, provider = await self.providers.generate_response(prompt)
        reply = _tidy(reply)
        if not reply or provider == "fallback":
            reply = generate_support_reply(msg, emotion_hint, mode if is_chat else "chat")
            provider = "local"

        return {
            "message": reply,
            "provider_used": provider,
            "intent": intent.intent,
            "detected_emotion": emotion,
            "safety": None,
        }


def _tidy(reply: str | None) -> str:
    """Trim, drop stray leading labels/markdown headings the model sometimes adds."""
    text = (reply or "").strip()
    text = re.sub(r"^(mindease|assistant)\s*[:\-]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^#{1,6}\s*", "", text)
    return text.strip()


ai_engine = AIEngine()
