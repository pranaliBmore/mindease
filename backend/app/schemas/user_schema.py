from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    avatar_url: Optional[str] = None
    bio: str = ""
    email_verified: bool = False
    emotional_history: List[str]
    feedback_history: List[str]
    communities: List[str]
    connections: List[str]
    created_at: datetime
