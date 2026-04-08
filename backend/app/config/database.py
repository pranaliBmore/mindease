from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config.settings import get_settings

settings = get_settings()
client = AsyncIOMotorClient(settings.mongodb_url)
db: AsyncIOMotorDatabase = client[settings.mongodb_db_name]


async def ensure_indexes() -> None:
    await db.users.create_index("email", unique=True)
    await db.emotions.create_index("user_id")
    await db.reasons.create_index("user_id")
    await db.chat_messages.create_index("user_id")
    await db.feedback.create_index("user_id")
    await db.connections.create_index([("user_id", 1), ("target_user_id", 1)], unique=True)
    await db.connection_requests.create_index([("from_user_id", 1), ("to_user_id", 1)], unique=True)
    await db.connection_requests.create_index([("to_user_id", 1), ("status", 1)])
    await db.direct_messages.create_index([("conversation_id", 1), ("created_at", -1)])
    await db.solo_analyses.create_index([("user_id", 1), ("created_at", -1)])
    await db.community_posts.create_index([("created_at", -1)])
    await db.communities.create_index("name", unique=True)
