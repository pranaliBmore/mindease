from fastapi import HTTPException, status

from app.config.database import db
from app.models.community_model import build_community_document
from app.services.community_feed_service import community_feed_service


class CommunityService:
    async def join(self, user: dict, community_name: str) -> dict:
        community_key = community_name.strip().lower()
        if not community_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="community_name is required")

        community = await db.communities.find_one({"name": community_key})
        if not community:
            await db.communities.insert_one(build_community_document(community_key))

        await db.communities.update_one(
            {"name": community_key},
            {"$addToSet": {"members": str(user["_id"])}},
        )
        await db.users.update_one({"_id": user["_id"]}, {"$addToSet": {"communities": community_key}})
        return {"message": f"Joined community: {community_key}"}

    async def get_details(self, community_name: str) -> dict:
        community_key = community_name.strip().lower()
        if not community_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="community_name is required")
        
        community = await db.communities.find_one({"name": community_key})
        member_count = len(community.get("members", [])) if community else 0
        feed = await community_feed_service.feed(limit=10, community_name=community_key)
        
        return {
            "name": community_key,
            "member_count": member_count,
            "recent_posts": feed["items"]
        }
