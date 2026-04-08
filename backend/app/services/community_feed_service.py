import uuid

from fastapi import HTTPException, status

from app.config.database import db
from app.services.ai_engine import ai_engine
from app.services.local_nlp import classify_emotion_vader
from app.utils.common import serialize_mongo_id, to_object_id, utc_now


class CommunityFeedService:
    async def create_post(self, user: dict, text: str, community_name: str | None = None) -> dict:
        clean = (text or "").strip()
        if not clean:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required")

        mood_result = classify_emotion_vader(clean)
        mood = mood_result.emotion

        engine = await ai_engine.respond(
            user_message=clean,
            conversation_history="",
            emotion_hint=mood,
            context_tag="community_post",
        )
        ai_reply = (engine.get("message") or "").strip()
        if not ai_reply:
            ai_reply = "I’m here with you. Would you like to share a bit more about what’s making this feel heavy today?"

        doc = {
            "user_id": str(user["_id"]),
            "text": clean,
            "mood": mood,
            "ai_reply": ai_reply,
            "likes": 0,
            "liked_by": [],
            "comments": [],
            "raw_comments": [],
            "community_name": community_name.strip().lower() if community_name else None,
            "created_at": utc_now(),
        }
        ins = await db.community_posts.insert_one(doc)
        doc["_id"] = ins.inserted_id
        return serialize_mongo_id(doc)

    async def feed(self, limit: int = 30, community_name: str | None = None) -> dict:
        cap = max(1, min(limit, 100))
        query = {}
        if community_name:
            query["community_name"] = community_name.strip().lower()
            
        rows = await db.community_posts.find(query).sort("created_at", -1).limit(cap).to_list(length=cap)
        items = [serialize_mongo_id(r) for r in rows]
        
        trending_rows = await db.community_posts.find({}).sort("likes", -1).limit(5).to_list(length=5)
        trending_posts = [serialize_mongo_id(r) for r in trending_rows]
        
        user_rows = await db.users.find({}, {"_id": 1, "name": 1}).sort("_id", -1).limit(5).to_list(length=5)
        suggested_users = [{"id": str(u["_id"]), "name": u.get("name", "User")} for u in user_rows]

        return {
            "items": items,
            "trending_posts": trending_posts,
            "suggested_users": suggested_users
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
                {"$pull": {"liked_by": uid}, "$inc": {"likes": -1}}
            )
            return {"message": "Unliked"}
        else:
            await db.community_posts.update_one(
                {"_id": oid}, 
                {"$addToSet": {"liked_by": uid}, "$inc": {"likes": 1}}
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
            
        new_comment = {"user_id": str(user["_id"]), "text": clean, "id": str(uuid.uuid4())}
        await db.community_posts.update_one(
            {"_id": oid}, 
            {"$push": {"raw_comments": new_comment, "comments": clean}}
        )
        return {"message": "Comment added"}

    async def seed_if_empty(self) -> None:
        existing = await db.community_posts.count_documents({})
        if existing:
            return
        now = utc_now()
        seed = [
            {"text": "Feeling low today, nothing is working.", "mood": "sadness"},
            {"text": "Had a stressful day at college. My mind won’t stop racing.", "mood": "stress"},
            {"text": "Trying to stay positive but it’s hard. Any small tips that helped you?", "mood": "anxiety"},
            {"text": "Anyone else feeling anxious lately? I’m worried about the future.", "mood": "fear"},
            {"text": "I snapped at someone and I regret it. I want to handle anger better.", "mood": "anger"},
            {"text": "Small win: I finally took a walk and felt lighter for a bit.", "mood": "happiness"},
            {"text": "Not sure what I feel—just kind of blank today.", "mood": "neutrality"},
        ]
        docs = []
        for item in seed:
            engine = await ai_engine.respond(
                user_message=item["text"],
                conversation_history="",
                emotion_hint=item["mood"],
                context_tag="community_seed",
            )
            docs.append(
                {
                    "user_id": "seed",
                    "text": item["text"],
                    "mood": item["mood"],
                    "ai_reply": engine["message"],
                    "likes": 0,
                    "liked_by": [],
                    "comments": [],
                    "raw_comments": [],
                    "created_at": now,
                }
            )
        await db.community_posts.insert_many(docs)


community_feed_service = CommunityFeedService()

