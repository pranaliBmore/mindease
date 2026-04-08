from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    emotion_context: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    provider_used: str
    intent: Optional[str] = None
    detected_emotion: Optional[str] = None


class ChatMessageItem(BaseModel):
    id: str
    user_message: str
    ai_reply: str
    provider_used: str
    created_at: datetime
