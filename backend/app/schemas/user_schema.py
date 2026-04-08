from datetime import datetime
from typing import List

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    emotional_history: List[str]
    feedback_history: List[str]
    communities: List[str]
    connections: List[str]
    created_at: datetime
