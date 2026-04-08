from app.config.database import db
from app.models.feedback_model import build_feedback_document
from app.utils.common import serialize_mongo_id


class FeedbackService:
    async def submit(self, user: dict, flow_type: str, content_type: str | None, message: str, rating: int) -> dict:
        feedback_doc = build_feedback_document(
            user_id=str(user["_id"]),
            flow_type=flow_type,
            content_type=content_type,
            message=message,
            rating=rating,
        )
        insert_result = await db.feedback.insert_one(feedback_doc)
        feedback_id = str(insert_result.inserted_id)
        await db.users.update_one({"_id": user["_id"]}, {"$push": {"feedback_history": feedback_id}})

        saved = await db.feedback.find_one({"_id": insert_result.inserted_id})
        return serialize_mongo_id(saved)
