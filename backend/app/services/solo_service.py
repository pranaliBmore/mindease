import json
import logging
import random
import re
import uuid
from typing import Any, Dict, List, Tuple

import httpx
from fastapi import HTTPException, status

from app.ai.providers import AIProviderService
from app.config.database import db
from app.config.settings import get_settings
from app.models.solo_model import build_solo_analysis_document
from app.services.local_nlp import classify_emotion_vader
from app.services.wellness_content import WELLNESS_CONTENT
from app.schemas.solo_schema import SoloEmotion
from app.utils.crypto import encrypt_text

logger = logging.getLogger(__name__)
settings = get_settings()


HF_ROUTER_MODEL_URL = "https://router.huggingface.co/hf-inference/models/{model}"

# Map GoEmotions labels into the app's required categories.
LABEL_TO_CATEGORY: dict[str, SoloEmotion] = {
    # Anger cluster
    "anger": "anger",
    "annoyance": "anger",
    "disapproval": "anger",
    "disgust": "anger",
    # Fear/anxiety cluster
    "fear": "fear",
    "nervousness": "anxiety",
    "confusion": "anxiety",
    "embarrassment": "anxiety",
    "remorse": "anxiety",
    # Sadness cluster
    "sadness": "sadness",
    "disappointment": "sadness",
    "grief": "sadness",
    # Happiness / positive affect cluster
    "joy": "happiness",
    "amusement": "happiness",
    "admiration": "happiness",
    "approval": "happiness",
    "gratitude": "happiness",
    "love": "happiness",
    "optimism": "happiness",
    "excitement": "happiness",
    "relief": "happiness",
    "pride": "happiness",
    "caring": "happiness",
    "desire": "happiness",
    # Neutral
    "neutral": "neutrality",
    # Surprise/realization/curiosity: treat as neutral unless strong; they are not negative by default.
    "surprise": "neutrality",
    "realization": "neutrality",
    "curiosity": "neutrality",
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _pick_reflection_sentence(text: str) -> str:
    cleaned = _normalize_text(text)
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return cleaned[:160]
    # Prefer a medium-length sentence.
    parts.sort(key=lambda s: abs(len(s) - 120))
    return parts[0][:220]


def _aggregate_categories(rows: list[dict]) -> Tuple[SoloEmotion, float, dict[str, float]]:
    buckets: dict[SoloEmotion, float] = {
        "stress": 0.0,
        "anxiety": 0.0,
        "sadness": 0.0,
        "happiness": 0.0,
        "anger": 0.0,
        "fear": 0.0,
        "neutrality": 0.0,
    }
    raw: dict[str, float] = {}
    for item in rows:
        label = str(item.get("label", "")).lower().strip()
        score = float(item.get("score", 0.0))
        if not label:
            continue
        raw[label] = max(raw.get(label, 0.0), score)
        cat = LABEL_TO_CATEGORY.get(label)
        if cat:
            buckets[cat] += score

    # Derive "stress" if we see both anxiety-ish and sadness-ish signals (common "stress" pattern).
    stress_signal = buckets["anxiety"] + 0.6 * buckets["sadness"] + 0.35 * buckets["anger"]
    buckets["stress"] = max(buckets["stress"], stress_signal)

    # Pick best.
    best_cat: SoloEmotion = max(buckets.keys(), key=lambda k: buckets[k])
    confidence = min(1.0, max(0.0, buckets[best_cat]))
    return best_cat, confidence, raw


def _curated_bank() -> dict[SoloEmotion, dict[str, list]]:
    """Randomised-per-request wellness content, keyed by mood. See wellness_content.py."""
    return WELLNESS_CONTENT


class SoloService:
    def __init__(self) -> None:
        self.ai = AIProviderService()

    async def _classify_emotion(self, text: str) -> Tuple[SoloEmotion, float, str]:
        if not text.strip():
            return "neutrality", 1.0, "empty_input"
            
        prompt = (
            "Analyze the sentiment of the following text and categorize it into EXACTLY ONE of these categories: "
            "stress, anxiety, sadness, happiness, anger, fear, neutrality.\n"
            "Return ONLY the category word, nothing else.\n\n"
            f"Text: \"{text}\""
        )
        reply, provider = await self.ai.generate_response(prompt)
        
        if provider != "fallback":
            reply = reply.strip().lower()
            valid = {"stress", "anxiety", "sadness", "happiness", "anger", "fear", "neutrality"}
            for v in valid:
                if v in reply:
                    return v, 0.9, f"llm_{provider}"

        logger.warning("Emotion LLM parsing failed or fell back. Using local NLP.")
        local = classify_emotion_vader(text)
        return local.emotion, local.confidence, local.model_used

    async def _generate_suggestions_llm(
        self,
        *,
        text: str,
        emotion: SoloEmotion,
        confidence: float,
        session_id: str,
    ) -> dict | None:
        reflection = _pick_reflection_sentence(text)
        prompt = (
            "You are MindEase, a supportive assistant for anxiety and confidence building. "
            "Given a user's journal text and an emotion classification, return ONLY valid JSON with exactly these keys:\n"
            "{\n"
            '  "exercises": [string, string, string],\n'
            '  "quotes": [string, string, string],\n'
            '  "tips": [string, string, string]\n'
            "}\n"
            "Constraints:\n"
            "- Items must be specific, practical, and not clinical.\n"
            "- Avoid repeating phrases.\n"
            "- Tailor to the user's text.\n"
            f"\nSession id: {session_id}\n"
            f"Detected emotion: {emotion}\n"
            f"Confidence: {confidence:.3f}\n"
            f"User text (excerpt): {reflection}\n"
        )
        reply, provider = await self.ai.generate_response(prompt)
        if provider == "fallback":
            return None
        # Extract JSON if provider adds extra text.
        start = reply.find("{")
        end = reply.rfind("}")
        if start < 0 or end < 0 or end <= start:
            return None
        try:
            parsed = json.loads(reply[start : end + 1])
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(parsed, dict):
            return None
        for k in ("exercises", "quotes", "tips"):
            if k not in parsed:
                return None
        return parsed

    def _generate_suggestions_curated(self, *, emotion: SoloEmotion, seed: str) -> dict:
        bank = _curated_bank()
        rnd = random.Random(seed)
        emo = emotion if emotion in bank else "neutrality"
        pack = bank[emo]
        exercises = rnd.sample(pack["exercises"], k=min(3, len(pack["exercises"])))
        quotes = rnd.sample(pack["quotes"], k=min(3, len(pack["quotes"])))
        tips = rnd.sample(pack["tips"], k=min(3, len(pack["tips"])))
        videos = rnd.sample(pack["videos"], k=min(2, len(pack["videos"])))
        rnd.shuffle(exercises)
        rnd.shuffle(quotes)
        rnd.shuffle(tips)
        rnd.shuffle(videos)
        return {"exercises": exercises, "quotes": quotes, "videos": videos, "tips": tips}

    async def analyze(self, user: dict, text: str, session_id: str | None) -> dict:
        clean = _normalize_text(text)
        sid = (session_id or "").strip() or uuid.uuid4().hex[:16]

        emotion, confidence, model_used = await self._classify_emotion(clean)

        # Try LLM personalization first; fall back to curated bank.
        suggestions = await self._generate_suggestions_llm(
            text=clean, emotion=emotion, confidence=confidence, session_id=sid
        )
        if not suggestions:
            suggestions = self._generate_suggestions_curated(emotion=emotion, seed=f"{sid}:{emotion}:{uuid.uuid4().hex}")
        elif "videos" not in suggestions:
            bank = _curated_bank()
            rnd = random.Random(sid)
            emo = emotion if emotion in bank else "neutrality"
            pack = bank[emo]
            videos = rnd.sample(pack["videos"], k=min(2, len(pack["videos"])))
            suggestions["videos"] = videos

        doc = build_solo_analysis_document(
            user_id=str(user["_id"]),
            session_id=sid,
            text=encrypt_text(clean),
            emotion=emotion,
            confidence=confidence,
            model_used=model_used,
            suggestions=suggestions,
        )
        await db.solo_analyses.insert_one(doc)

        return {
            "session_id": sid,
            "emotion": emotion,
            "confidence": confidence,
            "model_used": model_used,
            "suggestions": suggestions,
        }


solo_service = SoloService()

