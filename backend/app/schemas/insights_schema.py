from typing import Dict, List, Optional

from pydantic import BaseModel


class MoodCount(BaseModel):
    mood: str
    count: int


class InsightsResponse(BaseModel):
    period: str
    check_ins: int
    active_days: int
    top_mood: Optional[str] = None
    mood_breakdown: List[MoodCount]
    by_source: Dict[str, int]
    trend: str  # "improving" | "dipping" | "steady" | "not enough data"
    observations: List[str]
    generated_by: str  # "groq" | "huggingface" | ... | "local"
