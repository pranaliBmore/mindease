from typing import Literal, Optional

from pydantic import BaseModel, Field

SoloEmotion = Literal["stress", "anxiety", "sadness", "happiness", "anger", "fear", "neutrality"]


class SoloAnalyzeRequest(BaseModel):
    text: str = Field(default="", max_length=4000)
    session_id: Optional[str] = Field(default=None, max_length=64)


class SoloSuggestionPack(BaseModel):
    exercises: list[str]
    quotes: list[str]
    videos: list[dict]
    tips: list[str]


class SoloAnalyzeResponse(BaseModel):
    session_id: str
    emotion: SoloEmotion
    confidence: float = Field(ge=0.0, le=1.0)
    model_used: str
    suggestions: SoloSuggestionPack
