"""The Insights assistant.

Reads the signed-in user's own mood history - face-scan emotions, written
check-ins, AI chat conversations, and their community posts - and turns the
aggregate picture into a few gentle, plain-language observations.

Privacy: only aggregate numbers, mood labels and dates are ever sent to the
language model. The private notes / message text stay encrypted and untouched.
"""

import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.ai.providers import AIProviderService
from app.config.database import db
from app.utils.common import utc_now


def _aware(dt: datetime) -> datetime:
    """MongoDB returns UTC datetimes without tzinfo; make them comparable."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

logger = logging.getLogger(__name__)

_POSITIVE = {"happiness"}
_NEUTRAL = {"neutrality"}


def _valence(emotion: str) -> int:
    if emotion in _POSITIVE:
        return 1
    if emotion in _NEUTRAL:
        return 0
    return -1  # sadness, anger, fear, anxiety, stress


class InsightsService:
    def __init__(self) -> None:
        self.ai = AIProviderService()

    async def _collect(self, user_id: str, days: int) -> list[tuple]:
        cutoff = utc_now() - timedelta(days=days)
        q = {"user_id": user_id, "created_at": {"$gte": cutoff}}
        emo = await db.emotions.find(q, {"emotion": 1, "created_at": 1}).to_list(length=3000)
        solo = await db.solo_analyses.find(q, {"emotion": 1, "created_at": 1}).to_list(length=3000)
        posts = await db.community_posts.find(q, {"mood": 1, "created_at": 1}).to_list(length=3000)
        chats = await db.chat_messages.find(q, {"detected_emotion": 1, "created_at": 1}).to_list(length=3000)

        events: list[tuple] = []
        for r in emo:
            events.append((_aware(r["created_at"]), r.get("emotion") or "neutrality", "face scan"))
        for r in solo:
            events.append((_aware(r["created_at"]), r.get("emotion") or "neutrality", "written check-in"))
        for r in posts:
            events.append((_aware(r["created_at"]), r.get("mood") or "neutrality", "community post"))
        for r in chats:
            events.append((_aware(r["created_at"]), r.get("detected_emotion") or "neutrality", "AI chat"))
        events.sort(key=lambda e: e[0])
        return events

    async def summary(self, user: dict, range_: str) -> dict:
        days = 7 if range_ == "week" else 30
        events = await self._collect(str(user["_id"]), days)

        total = len(events)
        moods = Counter(e[1] for e in events)
        active_days = len({e[0].strftime("%Y-%m-%d") for e in events})
        by_source = Counter(e[2] for e in events)

        trend = "not enough data"
        if total >= 4:
            mid = utc_now() - timedelta(days=days / 2)
            first = [_valence(e[1]) for e in events if e[0] < mid]
            second = [_valence(e[1]) for e in events if e[0] >= mid]
            if first and second:
                delta = (sum(second) / len(second)) - (sum(first) / len(first))
                trend = "improving" if delta > 0.25 else "dipping" if delta < -0.25 else "steady"

        stats = {
            "period": "last 7 days" if days == 7 else "last 30 days",
            "check_ins": total,
            "active_days": active_days,
            "top_mood": moods.most_common(1)[0][0] if moods else None,
            "mood_breakdown": [{"mood": m, "count": c} for m, c in moods.most_common()],
            "by_source": dict(by_source),
            "trend": trend,
        }
        observations, generated_by = await self._observe(stats)
        return {**stats, "observations": observations, "generated_by": generated_by}

    async def _observe(self, stats: dict) -> tuple[list[str], str]:
        if not stats["check_ins"]:
            return (
                [
                    "You haven't logged any check-ins in this period yet.",
                    "Try a quick emotion scan or a written check-in - your patterns will show up here.",
                ],
                "local",
            )

        breakdown = ", ".join(f"{b['mood']} x{b['count']}" for b in stats["mood_breakdown"])
        facts = (
            f"Period: {stats['period']}. Check-ins: {stats['check_ins']} across {stats['active_days']} day(s). "
            f"Most common feeling: {stats['top_mood']}. Breakdown: {breakdown}. "
            f"Sources: {stats['by_source']}. Overall trend: {stats['trend']}."
        )
        prompt = (
            "You are MindEase's gentle insights assistant. Using ONLY the aggregate stats below "
            "about one person's mood check-ins (no private text is available), write 2 to 4 short, "
            "warm, plain-language observations they might find useful. Be encouraging and "
            "non-clinical. Do not invent anything that isn't in the stats. One sentence per line, "
            "no numbering, no headings.\n\n"
            f"Stats: {facts}\n\nObservations:\n"
        )
        try:
            reply, provider = await self.ai.generate_response(prompt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Insights AI call failed: %s", exc)
            reply, provider = "", "fallback"

        if provider != "fallback" and reply.strip():
            lines = [re.sub(r"^\s*[-*•\d.)]+\s*", "", ln).strip() for ln in reply.splitlines()]
            lines = [ln for ln in lines if len(ln) > 8][:4]
            if lines:
                return lines, provider
        return self._rule_observations(stats), "local"

    @staticmethod
    def _rule_observations(stats: dict) -> list[str]:
        out = [
            f"In the {stats['period']} you checked in {stats['check_ins']} time(s) "
            f"on {stats['active_days']} day(s)."
        ]
        if stats["top_mood"]:
            out.append(f"Your most frequent feeling was {stats['top_mood']}.")
        if stats["trend"] == "improving":
            out.append("Your recent check-ins lean a little more positive than earlier in the period.")
        elif stats["trend"] == "dipping":
            out.append(
                "Your recent check-ins have been a bit heavier than earlier. Be gentle with yourself "
                "and maybe try one small supportive step today."
            )
        elif stats["trend"] == "steady":
            out.append("Your mood has been fairly steady across the period.")
        if stats["active_days"] >= 3:
            out.append("Checking in regularly like this makes patterns easier to notice over time.")
        return out[:4]


insights_service = InsightsService()
