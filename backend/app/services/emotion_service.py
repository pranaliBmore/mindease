from fastapi import HTTPException, UploadFile, status

from app.config.database import db
from app.emotion_model.detector import analyze_emotion, decode_image
from app.models.emotion_model import build_emotion_document
from app.models.reason_model import build_reason_document
from app.utils.common import serialize_mongo_id, to_object_id


def _normalize_reason(reason: str | None) -> str | None:
    if reason is None:
        return None
    text = str(reason).strip()
    return text or None


class EmotionService:
    async def detect_and_store(
        self, user: dict, image_base64: str | None, image_file: UploadFile | None, reason: str | None
    ) -> dict:
        norm_reason = _normalize_reason(reason)
        frame = await decode_image(image_base64=image_base64, image_file=image_file)
        emotion, confidence, description = analyze_emotion(frame)
        emotion_doc = build_emotion_document(
            user_id=str(user["_id"]),
            emotion=emotion,
            confidence=confidence,
            description=description,
            reason=norm_reason,
        )
        insert_result = await db.emotions.insert_one(emotion_doc)
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$push": {"emotional_history": str(insert_result.inserted_id)}},
        )
        if norm_reason:
            await db.reasons.insert_one(
                build_reason_document(
                    user_id=str(user["_id"]),
                    emotion_id=str(insert_result.inserted_id),
                    text=norm_reason,
                )
            )
        return {
            "id": str(insert_result.inserted_id),
            "emotion": emotion,
            "confidence": confidence,
            "description": description,
        }

    async def attach_reason(self, user: dict, emotion_id: str, text: str | None) -> dict:
        norm = _normalize_reason(text)
        doc = await db.emotions.find_one({"_id": to_object_id(emotion_id), "user_id": str(user["_id"])})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emotion session not found")

        await db.emotions.update_one({"_id": doc["_id"]}, {"$set": {"reason": norm}})
        await db.reasons.delete_many({"emotion_id": emotion_id})
        if norm:
            await db.reasons.insert_one(
                build_reason_document(user_id=str(user["_id"]), emotion_id=emotion_id, text=norm),
            )
        return {"message": "Reason updated", "reason": norm}

    async def history(self, user: dict) -> list[dict]:
        cursor = db.emotions.find({"user_id": str(user["_id"])}).sort("created_at", -1).limit(50)
        items = await cursor.to_list(length=50)
        return [serialize_mongo_id(item) for item in items]
