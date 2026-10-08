import asyncio
import uuid

from fastapi import HTTPException, status

from app.config.database import db
from app.services.local_nlp import classify_emotion_vader
from app.utils.common import serialize_mongo_id, to_object_id, utc_now

_SEED_AUTHOR = {"id": "seed", "name": "MindEase Community", "avatar_url": None}


def _author_out(post: dict) -> dict:
    if post.get("user_id") == "seed":
        return _SEED_AUTHOR
    return {
        "id": post.get("user_id", ""),
        "name": post.get("author_name") or "A community member",
        "avatar_url": post.get("author_avatar_url"),
    }


def _comments_out(post: dict) -> list[dict]:
    out = []
    for c in post.get("raw_comments", []):
        out.append(
            {
                "id": c.get("id", ""),
                "user_id": c.get("user_id", ""),
                "name": c.get("name") or "A community member",
                "avatar_url": c.get("avatar_url"),
                "text": c.get("text", ""),
                "created_at": c.get("created_at"),
            },
        )
    return out


def _post_out(post: dict, viewer_id: str | None = None) -> dict:
    post["author"] = _author_out(post)
    post["comments"] = _comments_out(post)
    post["liked_by_me"] = bool(viewer_id) and viewer_id in post.get("liked_by", [])
    post.pop("raw_comments", None)
    post.pop("liked_by", None)
    post.pop("user_id", None)
    post.pop("author_name", None)
    post.pop("author_avatar_url", None)
    return serialize_mongo_id(post)


class CommunityFeedService:
    async def create_post(self, user: dict, text: str, community_name: str | None = None) -> dict:
        clean = (text or "").strip()
        if not clean:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required")

        mood_result = classify_emotion_vader(clean)
        mood = mood_result.emotion

        doc = {
            "user_id": str(user["_id"]),
            "author_name": user.get("name", ""),
            "author_avatar_url": user.get("avatar_url"),
            "text": clean,
            "mood": mood,
            "likes": 0,
            "liked_by": [],
            "raw_comments": [],
            "community_name": community_name.strip().lower() if community_name else None,
            "created_at": utc_now(),
        }
        ins = await db.community_posts.insert_one(doc)
        doc["_id"] = ins.inserted_id
        return _post_out(doc, viewer_id=str(user["_id"]))

    async def feed(self, limit: int = 30, community_name: str | None = None, viewer_id: str | None = None) -> dict:
        cap = max(1, min(limit, 100))
        query = {}
        if community_name:
            query["community_name"] = community_name.strip().lower()

        # These three reads are independent - running them concurrently instead of one
        # after another cuts this endpoint's latency to roughly the slowest single
        # query instead of the sum of all three.
        rows, trending_rows, user_rows = await asyncio.gather(
            db.community_posts.find(query).sort("created_at", -1).limit(cap).to_list(length=cap),
            db.community_posts.find({}).sort("likes", -1).limit(5).to_list(length=5),
            db.users.find({}, {"_id": 1, "name": 1}).sort("_id", -1).limit(5).to_list(length=5),
        )

        items = [_post_out(r, viewer_id) for r in rows]
        trending_posts = [_post_out(r, viewer_id) for r in trending_rows]
        suggested_users = [{"id": str(u["_id"]), "name": u.get("name", "User")} for u in user_rows]

        return {
            "items": items,
            "trending_posts": trending_posts,
            "suggested_users": suggested_users,
        }

    async def like(self, user: dict, post_id: str) -> dict:
        oid = to_object_id(post_id)
        uid = str(user["_id"])
        post = await db.community_posts.find_one({"_id": oid})
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        liked_by = post.get("liked_by", [])
        if uid in liked_by:
            await db.community_posts.update_one(
                {"_id": oid},
                {"$pull": {"liked_by": uid}, "$inc": {"likes": -1}},
            )
            return {"message": "Unliked"}
        else:
            await db.community_posts.update_one(
                {"_id": oid},
                {"$addToSet": {"liked_by": uid}, "$inc": {"likes": 1}},
            )
            return {"message": "Liked"}

    async def comment(self, user: dict, post_id: str, text: str) -> dict:
        oid = to_object_id(post_id)
        clean = (text or "").strip()
        if not clean:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment cannot be empty")

        post = await db.community_posts.find_one({"_id": oid})
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

        raw_comments = post.get("raw_comments", [])
        if raw_comments and raw_comments[-1].get("user_id") == str(user["_id"]) and raw_comments[-1].get("text") == clean:
            return {"message": "Comment suppressed (duplicate prevention)"}

        new_comment = {
            "id": str(uuid.uuid4()),
            "user_id": str(user["_id"]),
            "name": user.get("name", ""),
            "avatar_url": user.get("avatar_url"),
            "text": clean,
            "created_at": utc_now(),
        }
        await db.community_posts.update_one(
            {"_id": oid},
            {"$push": {"raw_comments": new_comment}},
        )
        return {"message": "Comment added"}

    async def seed_if_empty(self) -> None:
        existing = await db.community_posts.count_documents({})
        if existing:
            return
        now = utc_now()
        seed = [
            {"text": "Feeling low today, nothing is working.", "mood": "sadness"},
            {"text": "Had a stressful day at college. My mind won't stop racing.", "mood": "stress"},
            {"text": "Trying to stay positive but it's hard. Any small tips that helped you?", "mood": "anxiety"},
            {"text": "Anyone else feeling anxious lately? I'm worried about the future.", "mood": "fear"},
            {"text": "I snapped at someone and I regret it. I want to handle anger better.", "mood": "anger"},
            {"text": "Small win: I finally took a walk and felt lighter for a bit.", "mood": "happiness"},
            {"text": "Not sure what I feel, just kind of blank today.", "mood": "neutrality"},
            {"text": "Deadlines everywhere this week. Reminding myself I can only do one thing at a time.", "mood": "stress"},
            {"text": "Woke up at 3am with my heart pounding again. Anyone found something that helps?", "mood": "anxiety"},
            {"text": "Grateful for a friend who just listened today without trying to fix it.", "mood": "happiness"},
            {"text": "Missing someone a lot right now. Just needed to say it somewhere.", "mood": "sadness"},
            {"text": "Job interview tomorrow and my brain keeps playing the worst case on loop.", "mood": "fear"},
            {"text": "Frustrated with myself for procrastinating all day. Trying to be kinder about it.", "mood": "anger"},
            {"text": "Did a 5 minute breathing exercise before a meeting and it actually helped.", "mood": "happiness"},
            {"text": "Some days are just for getting through, and that's okay.", "mood": "neutrality"},
            {"text": "Started journaling this week. Weird at first, but it's helping me notice patterns.", "mood": "neutrality"},
            {"text": "Overwhelmed by the news. Taking a break from my phone for the evening.", "mood": "stress"},
            {"text": "Reached out to my sister after months. Nervous, but glad I did.", "mood": "anxiety"},
        ]
        docs = [
            {
                "user_id": "seed",
                "text": item["text"],
                "mood": item["mood"],
                "likes": 0,
                "liked_by": [],
                "raw_comments": [],
                "created_at": now,
            }
            for item in seed
        ]
        await db.community_posts.insert_many(docs)


community_feed_service = CommunityFeedService()
