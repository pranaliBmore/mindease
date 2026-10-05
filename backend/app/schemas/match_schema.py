from typing import Literal, Optional

from pydantic import BaseModel, Field

MatchMood = Literal["stress", "anxiety", "sadness", "happiness", "anger", "fear", "neutrality"]
MatchTopic = Literal["work_study", "relationships", "family", "health", "loneliness", "other"]
MatchSupportStyle = Literal["just_listen", "share_experience", "give_advice", "light_distraction"]
MatchGoal = Literal["feel_heard", "feel_less_alone", "get_practical_tips", "laugh_a_bit"]


class MatchStartRequest(BaseModel):
    mood: MatchMood
    topic: MatchTopic
    support_style: MatchSupportStyle
    goal: MatchGoal


class MatchSessionIdBody(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)


class MatchReportRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    reason: str = Field(default="", max_length=500)


class MatchSessionOut(BaseModel):
    session_id: str
    my_alias: str
    peer_alias: str
    status: Literal["active", "ended"]
    created_at: str


class MatchStateResponse(BaseModel):
    status: Literal["idle", "waiting", "matched"]
    session: Optional[MatchSessionOut] = None
    waiting_since: Optional[str] = None


class MatchMessageOut(BaseModel):
    id: str
    session_id: str
    from_user_id: str
    body: str
    created_at: Optional[str] = None
