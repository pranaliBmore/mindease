from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DetectEmotionRequest(BaseModel):
    image_base64: Optional[str] = None
    reason: Optional[str] = Field(default=None, max_length=500)


class EmotionResponse(BaseModel):
    id: str
    emotion: str
    confidence: float
    description: str


class AttachReasonRequest(BaseModel):
    emotion_id: str = Field(min_length=1, max_length=64)
    text: str = Field(default="", max_length=500)


class AttachReasonResponse(BaseModel):
    message: str
    reason: Optional[str] = None


class EmotionHistoryItem(BaseModel):
    id: str
    emotion: str
    confidence: float
    description: str
    reason: Optional[str]
    created_at: datetime
