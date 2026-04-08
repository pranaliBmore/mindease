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
from app.schemas.solo_schema import SoloEmotion

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
    # This is a large bank (not one static response) and is randomized per request.
    base_videos = {
        "stress": [
            {"title": "Box Breathing (4-4-4-4)", "url": "https://www.youtube.com/watch?v=tEmt1Znux58"},
            {"title": "5-Minute Reset for Stress", "url": "https://www.youtube.com/watch?v=ntfcfJ28eiU"},
        ],
        "anxiety": [
            {"title": "Grounding: 5-4-3-2-1", "url": "https://www.youtube.com/watch?v=30VMIEmA114"},
            {"title": "Short Anxiety Relief Meditation", "url": "https://www.youtube.com/watch?v=O-6f5wQXSu8"},
        ],
        "sadness": [
            {"title": "Self-Compassion Break", "url": "https://www.youtube.com/watch?v=rTFN8t9SXiQ"},
            {"title": "Gentle Mood Lift Walk", "url": "https://www.youtube.com/watch?v=0e5lM3pI7xY"},
        ],
        "happiness": [
            {"title": "Savoring Practice", "url": "https://www.youtube.com/watch?v=ZToicYcHIOU"},
            {"title": "Gratitude in 3 Minutes", "url": "https://www.youtube.com/watch?v=JMd1CcR3xXY"},
        ],
        "anger": [
            {"title": "Cooling Down Fast (Anger)", "url": "https://www.youtube.com/watch?v=BsVq5R_F6RA"},
            {"title": "Progressive Muscle Relaxation", "url": "https://www.youtube.com/watch?v=86HUcX8ZtAk"},
        ],
        "fear": [
            {"title": "Fear to Calm: Breath + Body", "url": "https://www.youtube.com/watch?v=1Dv-ldGLnIY"},
            {"title": "Safe Place Visualization", "url": "https://www.youtube.com/watch?v=IN5z4I6zBzs"},
        ],
        "neutrality": [
            {"title": "Check-In: Name the Feeling", "url": "https://www.youtube.com/watch?v=Zt9Mu5c9wqA"},
            {"title": "Mindful Minute", "url": "https://www.youtube.com/watch?v=Hzi3PDz1AWU"},
        ],
    }
    base_quotes = {
        "stress": [
            "You don’t have to do everything at once—just the next kind step.",
            "Even when you feel behind, your effort still counts.",
            "Breathe first. Then choose one small thing to steady yourself.",
        ],
        "anxiety": [
            "Anxiety is loud, but it isn’t always accurate.",
            "You can be scared and still be capable.",
            "Let the feeling be present without letting it drive.",
        ],
        "sadness": [
            "Sadness asks for gentleness, not speed.",
            "You’re allowed to take up space with what you feel.",
            "Small care is still real care.",
        ],
        "happiness": [
            "This moment matters—let yourself actually receive it.",
            "Joy grows when you notice it on purpose.",
            "Keep what works. Repeat what helps.",
        ],
        "anger": [
            "Anger often protects something important—listen without exploding.",
            "You can set boundaries without burning bridges.",
            "Strong feelings deserve skillful handling.",
        ],
        "fear": [
            "Courage is feeling fear and moving with care anyway.",
            "You can be uncertain and still be safe in this moment.",
            "Tiny steps are still forward.",
        ],
        "neutrality": [
            "Neutral is a valid state—use it to reset and choose intentionally.",
            "Clarity often arrives after a calm pause.",
            "Nothing urgent: just notice what you need next.",
        ],
    }
    base_exercises = {
        "stress": [
            "Two-minute box breathing: inhale 4, hold 4, exhale 4, hold 4—repeat 6 cycles.",
            "Brain dump: write the top 5 worries, then circle the one you can influence today.",
            "Shoulders + jaw release: 5 slow shoulder rolls, unclench jaw, exhale longer than inhale.",
        ],
        "anxiety": [
            "5-4-3-2-1 grounding: name 5 things you see… down to 1 thing you taste.",
            "Worry container: set a 10-minute timer to worry on paper, then stop when it ends.",
            "Label the sensation: “tight chest,” “fast thoughts”—name it, then breathe out slowly.",
        ],
        "sadness": [
            "Compassion note: write 3 lines to yourself as if to a friend.",
            "Tiny activation: stand up, drink water, open a window, and take 10 slow steps.",
            "Mood check: “What would make today 2% easier?” Do only that.",
        ],
        "happiness": [
            "Savoring: replay one good moment for 20 seconds, noticing colors/sounds/body feelings.",
            "Share it: text one person a simple win you noticed today.",
            "Gratitude specifics: write one thing you appreciate and why it mattered.",
        ],
        "anger": [
            "Physiological sigh: inhale, top-up inhale, long slow exhale—repeat 3 times.",
            "Boundary script: “When X happens, I feel Y. I need Z.” Write one sentence.",
            "Pause & cool: splash cold water or hold something cool for 30 seconds, then reassess.",
        ],
        "fear": [
            "Safety scan: name 3 signals that you’re safe right now (place, body, support).",
            "If-then plan: “If I start spiraling, then I will breathe + message someone.”",
            "Approach ladder: write the smallest next step (30 seconds) toward what you’re avoiding.",
        ],
        "neutrality": [
            "One-minute check-in: “What’s my energy level (0–10)?” “What do I need?”",
            "Micro-plan: choose 1 task, 1 break, 1 kindness for today.",
            "Mindful sip: drink water slowly and notice temperature and breath.",
        ],
    }
    base_tips = {
        "stress": [
            "Pick one priority for the next hour and let the rest wait.",
            "Lower the bar: define “good enough” for today in one sentence.",
            "If your body is tense, fix the body first—then think.",
        ],
        "anxiety": [
            "Ask: “Is this a possibility or a certainty?” Treat it like a possibility.",
            "Reduce inputs for 10 minutes (notifications, scrolling, caffeine).",
            "Choose the smallest next action and do it imperfectly.",
        ],
        "sadness": [
            "Don’t negotiate with yourself—do a tiny caring action first, feelings can follow.",
            "Reach for connection: a short message counts.",
            "Make your environment softer (light, warm drink, music).",
        ],
        "happiness": [
            "Capture the win: write one sentence so you can return to it later.",
            "Celebrate without minimizing—no “but…” for 60 seconds.",
            "Turn it into a habit: what helped today that you can repeat tomorrow?",
        ],
        "anger": [
            "Delay the reply: draft it, don’t send it, revisit in 20 minutes.",
            "Name the need under the anger (respect, safety, fairness).",
            "Move your body for 2 minutes to discharge adrenaline before speaking.",
        ],
        "fear": [
            "Anchor to what’s controllable: time, breath, next step, support.",
            "If it’s not dangerous right now, you can practice staying present for 30 seconds.",
            "Treat thoughts like weather—notice them, don’t obey them.",
        ],
        "neutrality": [
            "If you feel “nothing,” try “curious” instead of “stuck.”",
            "Neutral is a good time to plan: pick a tiny goal and a tiny reward.",
            "If you’re okay, protect it—take a small preventive break.",
        ],
    }
    return {
        cat: {
            "videos": base_videos[cat],
            "quotes": base_quotes[cat],
            "exercises": base_exercises[cat],
            "tips": base_tips[cat],
        }
        for cat in base_videos.keys()
    }


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
            text=clean,
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

