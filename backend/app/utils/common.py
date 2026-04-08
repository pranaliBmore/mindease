from datetime import datetime, timezone

from bson import ObjectId


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_object_id(value: str) -> ObjectId:
    return ObjectId(value)


def serialize_mongo_id(document: dict) -> dict:
    if "_id" in document:
        document["id"] = str(document.pop("_id"))
    return document
