"""Peer matching: pair a user with someone else based on a short mood/topic quiz.

Flow: start() either pairs the caller with the best-scoring person already waiting
(claimed atomically so two concurrent starts can't grab the same candidate), or
queues the caller until someone else starts a match. Pairing is identity-light by
design - participants see each other only as a random alias (e.g. "Calm Otter")
inside a match_session; either side can later "reveal" (sends a normal connection
request through the existing social graph) to become real, named connections.

Safety: report() ends the session and permanently blocks that pair from being
auto-matched again (match_blocks). Crisis-language detection on messages is
handled by the caller (see social_ws.py) reusing app.services.ai_engine.
"""

import logging
import random
from typing import Optional

from fastapi import HTTPException, status

from app.config.database import db
from app.models.match_model import build_queue_document, build_session_document
from app.utils.common import to_object_id, utc_now
from app.utils.crypto import decrypt_text, encrypt_text

logger = logging.getLogger(__name__)

NEGATIVE_MOODS = {"stress", "anxiety", "sadness", "anger", "fear"}
MAX_MATCH_MESSAGE_LENGTH = 2000

_ADJECTIVES = [
    "Calm", "Gentle", "Brave", "Quiet", "Hopeful", "Steady",
    "Kind", "Warm", "Bright", "Patient", "Soft", "Honest",
]
_ANIMALS = [
    "Fox", "Otter", "Owl", "Deer", "Sparrow", "Panda",
    "Falcon", "Dolphin", "Wolf", "Rabbit", "Heron", "Lynx",
]


def _random_alias() -> str:
    return f"{random.choice(_ADJECTIVES)} {random.choice(_ANIMALS)}"


def _two_distinct_aliases() -> tuple[str, str]:
    a = _random_alias()
    b = _random_alias()
    while b == a:
        b = _random_alias()
    return a, b


def _score(a: dict, b: dict) -> int:
    s = 0
    if a.get("topic") == b.get("topic"):
        s += 40
    if a.get("mood") == b.get("mood"):
        s += 20
    elif a.get("mood") in NEGATIVE_MOODS and b.get("mood") in NEGATIVE_MOODS:
        s += 10
    if a.get("support_style") == b.get("support_style"):
        s += 20
    if a.get("goal") == b.get("goal"):
        s += 20
    return s


def _pair_key(uid_a: str, uid_b: str) -> str:
    return ":".join(sorted([uid_a, uid_b]))


class MatchService:
    async def _is_blocked(self, uid_a: str, uid_b: str) -> bool:
        doc = await db.match_blocks.find_one({"pair_key": _pair_key(uid_a, uid_b)})
        return doc is not None

    async def _is_already_social(self, uid_a: str, uid_b: str) -> bool:
        """True if these two are already connected or have a pending request either way.
        Matching two people who already know each other defeats the point of an
        anonymous pairing, and re-revealing an existing connection is what caused
        duplicate connection rows - simplest fix is to never pair them again."""
        doc = await db.connection_requests.find_one(
            {
                "$or": [
                    {"from_user_id": uid_a, "to_user_id": uid_b, "status": {"$in": ["pending", "accepted"]}},
                    {"from_user_id": uid_b, "to_user_id": uid_a, "status": {"$in": ["pending", "accepted"]}},
                ],
            },
        )
        return doc is not None

    async def _active_session_for(self, uid: str) -> Optional[dict]:
        return await db.match_sessions.find_one(
            {"status": "active", "$or": [{"user_a": uid}, {"user_b": uid}]},
        )

    def _session_out(self, session: dict, uid: str) -> dict:
        is_a = session["user_a"] == uid
        return {
            "session_id": str(session["_id"]),
            "my_alias": session["alias_a"] if is_a else session["alias_b"],
            "peer_alias": session["alias_b"] if is_a else session["alias_a"],
            "status": session["status"],
            "created_at": session["created_at"].isoformat(),
        }

    async def state(self, user: dict) -> dict:
        uid = str(user["_id"])
        session = await self._active_session_for(uid)
        if session:
            return {"status": "matched", "session": self._session_out(session, uid), "waiting_since": None}
        q = await db.match_queue.find_one({"user_id": uid, "status": "waiting"})
        if q:
            return {"status": "waiting", "session": None, "waiting_since": q["created_at"].isoformat()}
        return {"status": "idle", "session": None, "waiting_since": None}

    async def start(self, user: dict, answers: dict) -> dict:
        uid = str(user["_id"])

        existing_session = await self._active_session_for(uid)
        if existing_session:
            return {"status": "matched", "session": self._session_out(existing_session, uid), "waiting_since": None}

        candidates = await db.match_queue.find(
            {"status": "waiting", "user_id": {"$ne": uid}},
        ).to_list(length=200)

        best = None
        best_score = -1
        for c in candidates:
            if await self._is_blocked(uid, c["user_id"]):
                continue
            if await self._is_already_social(uid, c["user_id"]):
                continue
            sc = _score(answers, c["answers"])
            if sc > best_score:
                best = c
                best_score = sc

        if best:
            # Atomic claim: if another concurrent /start already took this candidate,
            # find_one_and_delete returns None and we fall back to queueing instead.
            claimed = await db.match_queue.find_one_and_delete({"_id": best["_id"], "status": "waiting"})
            if not claimed:
                best = None

        if best:
            await db.match_queue.delete_many({"user_id": uid})
            peer_uid = best["user_id"]
            alias_a, alias_b = _two_distinct_aliases()
            doc = build_session_document(uid, peer_uid, alias_a, alias_b, answers, best["answers"], best_score)
            ins = await db.match_sessions.insert_one(doc)
            doc["_id"] = ins.inserted_id

            try:
                from app.realtime.social_manager import social_manager

                await social_manager.send_to_user(
                    peer_uid, {"type": "match_found", "session": self._session_out(doc, peer_uid)},
                )
            except Exception:  # noqa: BLE001
                logger.debug("WS notify match_found failed", exc_info=True)

            return {"status": "matched", "session": self._session_out(doc, uid), "waiting_since": None}

        queue_doc = build_queue_document(uid, answers)
        await db.match_queue.update_one(
            {"user_id": uid},
            {"$set": queue_doc},
            upsert=True,
        )
        return {"status": "waiting", "session": None, "waiting_since": queue_doc["created_at"].isoformat()}

    async def cancel(self, user: dict) -> dict:
        uid = str(user["_id"])
        await db.match_queue.delete_many({"user_id": uid})
        return {"message": "Left the matching queue"}

    async def _get_session_for_participant(self, user: dict, session_id: str) -> dict:
        uid = str(user["_id"])
        try:
            oid = to_object_id(session_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session id") from exc
        session = await db.match_sessions.find_one({"_id": oid, "$or": [{"user_a": uid}, {"user_b": uid}]})
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match session not found")
        return session

    async def list_messages(self, user: dict, session_id: str, limit: int = 100) -> list[dict]:
        session = await self._get_session_for_participant(user, session_id)
        cap = max(1, min(limit, 200))
        rows = await db.match_messages.find(
            {"session_id": str(session["_id"])},
        ).sort("created_at", 1).limit(cap).to_list(length=cap)
        return [
            {
                "id": str(r["_id"]),
                "session_id": r["session_id"],
                "from_user_id": r["from_user_id"],
                "body": decrypt_text(r["body"]),
                "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            }
            for r in rows
        ]

    async def send_message(self, user: dict, session_id: str, text: str) -> dict:
        clean = (text or "").strip()
        if not clean:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")
        if len(clean) > MAX_MATCH_MESSAGE_LENGTH:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message too long")
        session = await self._get_session_for_participant(user, session_id)
        if session["status"] != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This match has ended")

        uid = str(user["_id"])
        peer_uid = session["user_b"] if session["user_a"] == uid else session["user_a"]
        now = utc_now()
        doc = {
            "session_id": str(session["_id"]),
            "from_user_id": uid,
            "body": encrypt_text(clean),
            "created_at": now,
        }
        ins = await db.match_messages.insert_one(doc)
        return {
            "message": {
                "id": str(ins.inserted_id),
                "session_id": str(session["_id"]),
                "from_user_id": uid,
                "body": clean,
                "created_at": now.isoformat(),
            },
            "peer_user_id": peer_uid,
        }

    async def reveal(self, user: dict, session_id: str) -> dict:
        session = await self._get_session_for_participant(user, session_id)
        uid = str(user["_id"])
        peer_uid = session["user_b"] if session["user_a"] == uid else session["user_a"]

        from app.services.social_service import social_service

        return await social_service.send_request(user, target_user_id=peer_uid)

    async def end(self, user: dict, session_id: str, reason: str = "ended") -> dict:
        session = await self._get_session_for_participant(user, session_id)
        uid = str(user["_id"])
        peer_uid = session["user_b"] if session["user_a"] == uid else session["user_a"]
        await db.match_sessions.update_one(
            {"_id": session["_id"]},
            {"$set": {"status": "ended", "ended_at": utc_now(), "end_reason": reason}},
        )
        try:
            from app.realtime.social_manager import social_manager

            payload = {"type": "match_ended", "session_id": str(session["_id"])}
            await social_manager.send_to_user(peer_uid, payload)
            await social_manager.send_to_user(uid, payload)
        except Exception:  # noqa: BLE001
            logger.debug("WS notify match_ended failed", exc_info=True)
        return {"message": "Match ended"}

    async def report(self, user: dict, session_id: str, reason: str) -> dict:
        session = await self._get_session_for_participant(user, session_id)
        uid = str(user["_id"])
        peer_uid = session["user_b"] if session["user_a"] == uid else session["user_a"]
        await db.match_reports.insert_one(
            {
                "session_id": str(session["_id"]),
                "reporter_id": uid,
                "reported_user_id": peer_uid,
                "reason": (reason or "").strip()[:500],
                "created_at": utc_now(),
            },
        )
        await db.match_blocks.update_one(
            {"pair_key": _pair_key(uid, peer_uid)},
            {"$setOnInsert": {"pair_key": _pair_key(uid, peer_uid), "created_at": utc_now()}},
            upsert=True,
        )
        await self.end(user, session_id, reason="reported")
        return {"message": "Report submitted. This match has ended and you won't be paired with them again."}


match_service = MatchService()
