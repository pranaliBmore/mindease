import random
import re

from app.services.local_nlp import classify_emotion_vader


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def generate_support_reply(message: str, emotion_hint: str | None) -> str:
    """
    Non-static offline reply generator. Uses local NLP (VADER) + randomized response frames.
    """
    msg = _normalize(message)
    local = classify_emotion_vader(msg)
    emotion = (emotion_hint or "").strip().lower() or local.emotion

    rnd = random.Random(f"{local.emotion}:{hash(msg)}")

    openings = [
        "I’m here with you.",
        "Thanks for sharing that with me.",
        "That sounds like a lot to carry.",
        "I hear you.",
        "I’m glad you reached out.",
    ]
    reflections = [
        "If you had to name the strongest feeling in one word, what would it be?",
        "Where do you feel this most in your body right now (chest, stomach, jaw, shoulders)?",
        "What’s the hardest part of this moment?",
        "What do you need most right now: calm, clarity, confidence, or comfort?",
        "What’s one small next step that would make this 2% easier?",
    ]

    emotion_actions = {
        "stress": [
            "Try box breathing for 60 seconds: inhale 4, hold 4, exhale 4, hold 4.",
            "Pick one thing for the next 10 minutes. Everything else can wait.",
            "Do a quick reset: unclench jaw, drop shoulders, slow your exhale.",
        ],
        "anxiety": [
            "Let’s ground: name 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste.",
            "Ask: is this a possibility or a certainty? Treat it like a possibility for now.",
            "Try a long exhale: inhale 4, exhale 6, repeat 6 times.",
        ],
        "sadness": [
            "Be gentle with yourself—sadness often needs care, not pressure.",
            "A tiny caring action can help: water, food, shower, or a short walk.",
            "If you can, message one person: “Could you talk for 5 minutes?”",
        ],
        "happiness": [
            "Let’s savor it for 20 seconds—what exactly feels good about it?",
            "Would you like to anchor this moment with a short note so you can revisit it later?",
            "What helped create this feeling that you could repeat tomorrow?",
        ],
        "anger": [
            "Before responding to anyone, let’s cool the body first (long exhale or a quick walk).",
            "Anger often protects a need—what feels crossed: respect, fairness, or safety?",
            "If you want, we can write a boundary sentence together.",
        ],
        "fear": [
            "You’re not alone—let’s find what’s controllable in the next 5 minutes.",
            "Try a safety scan: name 3 signs you’re safe right now.",
            "If it’s not dangerous right now, we can take one tiny step together.",
        ],
        "neutrality": [
            "Neutral is okay—sometimes it’s a reset point.",
            "Want to check in: what’s your energy from 0–10?",
            "What would you like to focus on: calm, focus, or connection?",
        ],
    }

    action = rnd.choice(emotion_actions.get(emotion, emotion_actions["neutrality"]))
    opening = rnd.choice(openings)
    question = rnd.choice(reflections)

    return f"{opening} {action} {question}"

