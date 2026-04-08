from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    flow_type: Literal["with_flow", "without_flow"]
    content_type: Optional[Literal["quotes", "exercises", "videos"]] = None
    message: str = Field(min_length=2, max_length=1000)
    rating: int = Field(ge=1, le=5)


class FeedbackResponse(BaseModel):
    id: str
    flow_type: str
    content_type: Optional[str]
    message: str
    rating: int
    created_at: datetime
