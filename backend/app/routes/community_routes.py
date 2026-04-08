from fastapi import APIRouter, Depends, Query

from app.controllers.community_controller import join_community_controller, get_community_controller
from app.middleware.auth_middleware import get_current_user
from app.schemas.community_schema import GenericMessageResponse, JoinCommunityRequest
from app.schemas.community_feed_schema import (
    CommunityCommentRequest,
    CommunityFeedResponse,
    CommunityDetailResponse,
    CommunityLikeRequest,
    CommunityPostCreateRequest,
    CommunityPostOut,
)
from app.services.community_feed_service import community_feed_service

router = APIRouter(prefix="/api/community", tags=["community"])


@router.post("/join", response_model=GenericMessageResponse)
async def join_community(payload: JoinCommunityRequest, current_user: dict = Depends(get_current_user)):
    return await join_community_controller(current_user, payload.community_name)


@router.get("/details/{community_name}", response_model=CommunityDetailResponse)
async def get_community_details(community_name: str, current_user: dict = Depends(get_current_user)):
    return await get_community_controller(community_name)


@router.get("/feed", response_model=CommunityFeedResponse)
async def community_feed(
    limit: int = Query(30, ge=1, le=100), 
    community_name: str | None = Query(None),
    current_user: dict = Depends(get_current_user)
):
    return await community_feed_service.feed(limit=limit, community_name=community_name)


@router.post("/post", response_model=CommunityPostOut)
async def community_post(payload: CommunityPostCreateRequest, current_user: dict = Depends(get_current_user)):
    return await community_feed_service.create_post(current_user, payload.text, payload.community_name)


@router.post("/like", response_model=GenericMessageResponse)
async def community_like(payload: CommunityLikeRequest, current_user: dict = Depends(get_current_user)):
    return await community_feed_service.like(current_user, payload.post_id)


@router.post("/comment", response_model=GenericMessageResponse)
async def community_comment(payload: CommunityCommentRequest, current_user: dict = Depends(get_current_user)):
    return await community_feed_service.comment(current_user, payload.post_id, payload.text)
