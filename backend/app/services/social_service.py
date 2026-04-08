import logging
import re
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.config.database import db
from app.utils.common import serialize_mongo_id, to_object_id, utc_now

logger = logging.getLogger(__name__)

MAX_DM_LENGTH = 2000


def mask_email(email: str) -> str:
    email = (email or "").strip().lower()
    if "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"


def conversation_id(a: str, b: str) -> str:
    return ":".join(sorted([a, b]))


def public_user(user_doc: dict) -> dict:
    return {
        "id": str(user_doc["_id"]),
        "name": user_doc.get("name", ""),
        "email_masked": mask_email(user_doc.get("email", "")),
    }


class SocialService:
    async def are_connected(self, user_id_a: str, user_id_b: str) -> bool:
        doc = await db.connection_requests.find_one(
            {
                "$or": [
                    {"from_user_id": user_id_a, "to_user_id": user_id_b, "status": "accepted"},
                    {"from_user_id": user_id_b, "to_user_id": user_id_a, "status": "accepted"},
                ],
            },
        )
        if doc:
            return True
        ua = await db.users.find_one({"_id": to_object_id(user_id_a)})
        ub = await db.users.find_one({"_id": to_object_id(user_id_b)})
        if not ua or not ub:
            return False
        con_a = set(ua.get("connections") or [])
        con_b = set(ub.get("connections") or [])
        return user_id_b in con_a and user_id_a in con_b

    async def search_users(self, user: dict, q: str) -> list[dict]:
        raw = (q or "").strip()
        if len(raw) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search query must be at least 2 characters.",
            )
        esc = re.escape(raw)
        regex = {"$regex": esc, "$options": "i"}
        cursor = (
            db.users.find(
                {
                    "_id": {"$ne": user["_id"]},
                    "$or": [{"name": regex}, {"email": regex}],
                },
            )
            .limit(25)
        )
        items = await cursor.to_list(length=25)
        return [public_user(u) for u in items]

    async def send_request(
        self,
        user: dict,
        target_user_email: str | None = None,
        target_user_id: str | None = None,
    ) -> dict:
        target = None
        if target_user_id and str(target_user_id).strip():
            try:
                target = await db.users.find_one({"_id": to_object_id(str(target_user_id).strip())})
            except Exception:  # noqa: BLE001
                target = None
        elif target_user_email and str(target_user_email).strip():
            email = str(target_user_email).strip().lower()
            if "@" not in email:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email")
            target = await db.users.find_one({"email": email})
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide target_user_email or target_user_id",
            )
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        from_uid = str(user["_id"])
        to_uid = str(target["_id"])
        if from_uid == to_uid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot connect to yourself")

        reverse = await db.connection_requests.find_one(
            {"from_user_id": to_uid, "to_user_id": from_uid, "status": "pending"},
        )
        if reverse:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This person already sent you a request. Accept it under Pending requests.",
            )

        existing = await db.connection_requests.find_one({"from_user_id": from_uid, "to_user_id": to_uid})
        now = utc_now()
        if existing:
            if existing["status"] == "pending":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request already sent")
            if existing["status"] == "accepted":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already connected")
            await db.connection_requests.update_one(
                {"_id": existing["_id"]},
                {"$set": {"status": "pending", "updated_at": now}},
            )
        else:
            await db.connection_requests.insert_one(
                {
                    "from_user_id": from_uid,
                    "to_user_id": to_uid,
                    "status": "pending",
                    "created_at": now,
                    "updated_at": now,
                },
            )

        try:
            from app.realtime.social_manager import social_manager

            await social_manager.send_to_user(to_uid, {"type": "connection_state_changed"})
            await social_manager.send_to_user(from_uid, {"type": "connection_state_changed"})
        except Exception:  # noqa: BLE001
            logger.debug("WS notify after request failed", exc_info=True)

        return {"message": f"Connection request sent to {mask_email(target['email'])}"}

    async def connection_state(self, user: dict) -> dict:
        uid = str(user["_id"])
        incoming = await db.connection_requests.find({"to_user_id": uid, "status": "pending"}).to_list(length=100)
        outgoing = await db.connection_requests.find({"from_user_id": uid, "status": "pending"}).to_list(length=100)
        accepted = await db.connection_requests.find(
            {
                "$or": [
                    {"from_user_id": uid, "status": "accepted"},
                    {"to_user_id": uid, "status": "accepted"},
                ],
            },
        ).to_list(length=200)

        async def with_other(req: dict, other_field: str) -> dict:
            other_id = req[other_field]
            ou = await db.users.find_one({"_id": to_object_id(other_id)})
            other = public_user(ou) if ou else {"id": other_id, "name": "Unknown", "email_masked": "***"}
            return {
                "request_id": str(req["_id"]),
                "user": other,
                "created_at": req["created_at"].isoformat() if req.get("created_at") else None,
            }

        incoming_enriched = []
        for r in incoming:
            incoming_enriched.append(await with_other(r, "from_user_id"))

        outgoing_enriched = []
        for r in outgoing:
            outgoing_enriched.append(await with_other(r, "to_user_id"))

        connections_enriched = []
        for r in accepted:
            other_id = r["to_user_id"] if r["from_user_id"] == uid else r["from_user_id"]
            ou = await db.users.find_one({"_id": to_object_id(other_id)})
            other = public_user(ou) if ou else {"id": other_id, "name": "Unknown", "email_masked": "***"}
            at = r.get("updated_at") or r.get("created_at")
            connections_enriched.append(
                {
                    "request_id": str(r["_id"]),
                    "user": other,
                    "accepted_at": at.isoformat() if at else None,
                },
            )

        return {
            "incoming_pending": incoming_enriched,
            "outgoing_pending": outgoing_enriched,
            "connections": connections_enriched,
        }

    async def accept_request(self, user: dict, request_id: str) -> dict:
        uid = str(user["_id"])
        try:
            oid = to_object_id(request_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request id") from exc
        req = await db.connection_requests.find_one({"_id": oid, "to_user_id": uid, "status": "pending"})
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
        now = utc_now()
        await db.connection_requests.update_one(
            {"_id": oid},
            {"$set": {"status": "accepted", "updated_at": now}},
        )
        a, b = req["from_user_id"], req["to_user_id"]
        await db.users.update_one({"_id": to_object_id(a)}, {"$addToSet": {"connections": b}})
        await db.users.update_one({"_id": to_object_id(b)}, {"$addToSet": {"connections": a}})
        try:
            from app.realtime.social_manager import social_manager

            await social_manager.send_to_user(a, {"type": "connection_state_changed"})
            await social_manager.send_to_user(b, {"type": "connection_state_changed"})
        except Exception:  # noqa: BLE001
            logger.debug("WS notify after accept failed", exc_info=True)
        return {"message": "Connection accepted"}

    async def reject_request(self, user: dict, request_id: str) -> dict:
        uid = str(user["_id"])
        try:
            oid = to_object_id(request_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request id") from exc
        req = await db.connection_requests.find_one({"_id": oid, "to_user_id": uid, "status": "pending"})
        if not req:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
        from_uid = req["from_user_id"]
        await db.connection_requests.update_one(
            {"_id": oid},
            {"$set": {"status": "rejected", "updated_at": utc_now()}},
        )
        try:
            from app.realtime.social_manager import social_manager

            await social_manager.send_to_user(from_uid, {"type": "connection_state_changed"})
            await social_manager.send_to_user(uid, {"type": "connection_state_changed"})
        except Exception:  # noqa: BLE001
            logger.debug("WS notify after reject failed", exc_info=True)
        return {"message": "Request declined"}

    async def list_messages(self, user: dict, peer_user_id: str, limit: int = 80) -> list[dict]:
        uid = str(user["_id"])
        if not await self.are_connected(uid, peer_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not connected to this user")
        cid = conversation_id(uid, peer_user_id)
        cap = max(1, min(limit, 200))
        cursor = db.direct_messages.find({"conversation_id": cid}).sort("created_at", -1).limit(cap)
        rows = await cursor.to_list(length=cap)
        rows.reverse()
        out: list[dict] = []
        for row in rows:
            out.append(
                {
                    "id": str(row["_id"]),
                    "from_user_id": row["from_user_id"],
                    "to_user_id": row["to_user_id"],
                    "body": row["body"],
                    "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
                },
            )
        return out

    async def create_dm(
        self,
        sender: dict,
        to_user_id: str,
        body: str,
    ) -> dict[str, Any]:
        text = (body or "").strip()
        if not text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")
        if len(text) > MAX_DM_LENGTH:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message too long")
        from_uid = str(sender["_id"])
        if from_uid == to_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid recipient")
        if not await self.are_connected(from_uid, to_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not connected to this user")
        cid = conversation_id(from_uid, to_user_id)
        now = utc_now()
        doc = {
            "conversation_id": cid,
            "from_user_id": from_uid,
            "to_user_id": to_user_id,
            "body": text,
            "created_at": now,
        }
        ins = await db.direct_messages.insert_one(doc)
        return {
            "id": str(ins.inserted_id),
            "from_user_id": from_uid,
            "to_user_id": to_user_id,
            "body": text,
            "created_at": now.isoformat(),
        }


social_service = SocialService()
