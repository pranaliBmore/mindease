from fastapi import APIRouter, Response

from app.controllers.auth_controller import get_avatar_controller

router = APIRouter(prefix="/api/avatars", tags=["avatars"])


@router.get("/{user_id}")
async def get_avatar(user_id: str):
    """Public - avatars render in plain <img> tags across Discover/Community, which
    can't attach an Authorization header. Stored bytes, not a redirect, so this works
    the same whether the image lives in MongoDB or (later) object storage."""
    avatar = await get_avatar_controller(user_id)
    return Response(
        content=avatar["data"],
        media_type=avatar["content_type"],
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
