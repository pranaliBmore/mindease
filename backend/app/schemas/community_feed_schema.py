from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Mood = Literal["stress", "anxiety", "sadness", "happiness", "anger", "fear", "neutrality"]


class CommunityPostCreateRequest(BaseModel):
    text: str = Field(min_length=2, max_length=2000)
    community_name: Optional[str] = None


class CommunityLikeRequest(BaseModel):
    post_id: str = Field(min_length=1, max_length=64)


class PostAuthor(BaseModel):
    id: str
    name: str
    avatar_url: Optional[str] = None


class CommunityPostOut(BaseModel):
    id: str
    author: PostAuthor
    text: str
    mood: Mood
    created_at: datetime
    ai_reply: str
    likes: int = 0
    community_name: Optional[str] = None

class CommunityDetailResponse(BaseModel):
    name: str
    member_count: int
    recent_posts: list[CommunityPostOut]


class SuggestedUser(BaseModel):
    id: str
    name: str

class CommunityFeedResponse(BaseModel):
    items: list[CommunityPostOut]
    trending_posts: list[CommunityPostOut] = []
    suggested_users: list[SuggestedUser] = []

