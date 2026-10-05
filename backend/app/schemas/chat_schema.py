from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# Optional guided modes the chat UI can request via its tool buttons.
ChatMode = Literal["chat", "breathing", "grounding", "journal_prompt", "reframe", "pep_talk"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    emotion_context: Optional[str] = None
    mode: ChatMode = "chat"


class ChatResponse(BaseModel):
    reply: str
    provider_used: str
    intent: Optional[str] = None
    detected_emotion: Optional[str] = None
    safety: Optional[str] = None  # set to "crisis" when a crisis-support reply was returned


class ChatMessageItem(BaseModel):
    id: str
    user_message: str
    ai_reply: str
    provider_used: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageItem]


class GenericMessageResponse(BaseModel):
    message: str
