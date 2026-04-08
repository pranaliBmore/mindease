from pydantic import BaseModel, Field, model_validator


class JoinCommunityRequest(BaseModel):
    community_name: str = Field(min_length=2, max_length=100)


class ConnectionRequest(BaseModel):
    target_user_email: str | None = None
    target_user_id: str | None = None

    @model_validator(mode="after")
    def require_one_target(self) -> "ConnectionRequest":
        email_ok = bool(self.target_user_email and str(self.target_user_email).strip())
        id_ok = bool(self.target_user_id and str(self.target_user_id).strip())
        if not email_ok and not id_ok:
            raise ValueError("Provide target_user_email or target_user_id")
        return self


class ConnectionRequestIdBody(BaseModel):
    request_id: str = Field(min_length=1, max_length=64)


class GenericMessageResponse(BaseModel):
    message: str
