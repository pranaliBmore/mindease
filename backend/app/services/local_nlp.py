import math
import re
from dataclasses import dataclass

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.schemas.solo_schema import SoloEmotion


_analyzer = SentimentIntensityAnalyzer()


@dataclass(frozen=True)
class LocalEmotionResult:
    emotion: SoloEmotion
    confidence: float
    model_used: str


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def classify_emotion_vader(text: str) -> LocalEmotionResult:
    """
    Lightweight local NLP fallback. Uses VADER (lexicon + rules) to estimate affect polarity
    and maps it into the app's emotion categories. This is used ONLY when HF is unavailable.
    """
    t = _normalize_text(text)
    # Light lexical cues to disambiguate *within* the VADER fallback.
    # (Primary signal is still the VADER affect score; these only adjust borderline cases.)
    t_low = t.lower()
    if re.search(r"\b(stress|stressed|burnt out|overwhelmed)\b", t_low):
        return LocalEmotionResult("stress", 0.6, "vaderSentiment")
    if re.search(r"\b(anxious|anxiety|panic|panicking|worried|worry)\b", t_low):
        return LocalEmotionResult("anxiety", 0.6, "vaderSentiment")
    if re.search(r"\b(angry|furious|rage)\b", t_low):
        return LocalEmotionResult("anger", 0.6, "vaderSentiment")
    if re.search(r"\b(scared|afraid|fear)\b", t_low):
        return LocalEmotionResult("fear", 0.6, "vaderSentiment")
    if re.search(r"\b(sad|down|depressed|hopeless)\b", t_low):
        return LocalEmotionResult("sadness", 0.6, "vaderSentiment")
    scores = _analyzer.polarity_scores(t)
    compound = float(scores.get("compound", 0.0))  # [-1, 1]
    neg = float(scores.get("neg", 0.0))
    pos = float(scores.get("pos", 0.0))

    # Confidence heuristic: stronger compound → higher confidence.
    # Map |compound| in [0,1] to [0.5, 0.95] so we still communicate uncertainty.
    strength = abs(compound)
    confidence = 0.5 + 0.45 * _clamp01(strength)

    if compound >= 0.35:
        return LocalEmotionResult("happiness", confidence, "vaderSentiment")
    if compound <= -0.35:
        # When strongly negative, choose anger vs sadness vs fear based on neg dominance.
        if neg >= 0.55 and pos < 0.1:
            return LocalEmotionResult("sadness", confidence, "vaderSentiment")
        if neg >= 0.45 and "!" in t:
            return LocalEmotionResult("anger", confidence, "vaderSentiment")
        return LocalEmotionResult("stress", confidence, "vaderSentiment")

    # Near-neutral: decide between neutrality/anxiety/stress based on slight negativity and arousal.
    if neg > 0.25 and pos < 0.15:
        return LocalEmotionResult("anxiety", 0.55, "vaderSentiment")
    return LocalEmotionResult("neutrality", 0.55, "vaderSentiment")

