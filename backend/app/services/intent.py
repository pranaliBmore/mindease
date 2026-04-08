import re
from dataclasses import dataclass


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: float


def classify_intent(text: str) -> IntentResult:
    """
    Lightweight intent classifier. This is a hybrid approach intended for reliability and speed.
    It does NOT replace the generative model; it guides response style and follow-ups.
    """
    t = re.sub(r"\s+", " ", (text or "").strip()).lower()
    if not t:
        return IntentResult("empty", 1.0)

    if re.search(r"\b(help|what should i do|can you help|support me)\b", t):
        return IntentResult("help_request", 0.8)
    if re.search(r"\b(exam|interview|presentation|deadline|job)\b", t):
        return IntentResult("performance_stress", 0.65)
    if re.search(r"\b(why|how|what|when|where)\b.*\?", t) or t.endswith("?"):
        return IntentResult("question", 0.7)
    if re.search(r"\b(motivat|inspire|confidence|encourage)\b", t):
        return IntentResult("motivation", 0.7)
    if re.search(r"\b(thanks|thank you|appreciate)\b", t):
        return IntentResult("gratitude", 0.7)

    return IntentResult("general_talk", 0.55)

