"""Private aggregate reporting for interactive child practice."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, status

from ..database import get_database
from ..models.interactive_session import InteractiveSessionCreate
from ..utils.jwt_handler import get_current_user


router = APIRouter(prefix="/api/interactive-sessions", tags=["interactive-sessions"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def build_interactive_summary(rows: list[dict[str, Any]], reference: datetime | None = None) -> dict[str, Any]:
    """Build an honest seven-day roll-up from one authenticated user's rows."""
    reference = _as_utc(reference or utc_now())
    week_start = reference - timedelta(days=7)
    recent = [
        row for row in rows
        if isinstance(row.get("created_at"), datetime) and _as_utc(row["created_at"]) >= week_start
    ]
    if not recent:
        return {
            "sessions_this_week": 0,
            "communication_turns": 0,
            "independent_percentage": 0,
            "most_practised_activity": None,
            "assistance_trend": [],
            "recommendation": "Complete a Play & Practice activity to begin the private progress summary.",
        }

    activity_counts = Counter(row.get("activity_id") for row in recent if row.get("activity_id"))
    assistance_totals: Counter[str] = Counter()
    daily: dict[str, Counter[str]] = defaultdict(Counter)
    for row in recent:
        counts = row.get("assistance_counts") or {}
        day = _as_utc(row["created_at"]).date().isoformat()
        for name in ("independent", "verbal_prompt", "visual_prompt", "modelled", "skipped"):
            value = max(0, int(counts.get(name, 0) or 0))
            assistance_totals[name] += value
            daily[day][name] += value

    supported_turns = sum(assistance_totals.values())
    independent_percentage = int(
        assistance_totals["independent"] / supported_turns * 100 + 0.5
    ) if supported_turns else 0
    trend = []
    for day in sorted(daily):
        total = sum(daily[day].values())
        trend.append({
            "date": day,
            "independent_percentage": int(daily[day]["independent"] / total * 100 + 0.5) if total else 0,
            "support_turns": total - daily[day]["independent"],
        })

    if independent_percentage >= 75:
        recommendation = "Keep the same short routine and offer time to respond independently."
    elif assistance_totals["modelled"] or assistance_totals["visual_prompt"]:
        recommendation = "Try one visual cue, wait, and celebrate every communication attempt."
    else:
        recommendation = "Use a short verbal prompt, then leave a quiet pause for a response."

    return {
        "sessions_this_week": len(recent),
        "communication_turns": sum(max(0, int(row.get("communication_turns", 0) or 0)) for row in recent),
        "independent_percentage": independent_percentage,
        "most_practised_activity": activity_counts.most_common(1)[0][0] if activity_counts else None,
        "assistance_trend": trend,
        "recommendation": recommendation,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_interactive_session(
    payload: InteractiveSessionCreate,
    current_user: dict = Depends(get_current_user),
):
    """Store safe aggregate counts under the authenticated owner's ID."""
    db = get_database()
    document = {
        **payload.model_dump(),
        "assistance_counts": payload.assistance_counts.model_dump(),
        "user_id": str(current_user["_id"]),
        "created_at": utc_now(),
    }
    result = await db.interactive_sessions.insert_one(document)
    return {"id": str(result.inserted_id), "status": "recorded"}


@router.get("/summary")
async def interactive_session_summary(current_user: dict = Depends(get_current_user)):
    """Return the caller's private seven-day aggregate summary."""
    db = get_database()
    reference = utc_now()
    rows = await db.interactive_sessions.find({
        "user_id": str(current_user["_id"]),
        "created_at": {"$gte": reference - timedelta(days=7)},
    }).sort("created_at", -1).limit(500).to_list(length=500)
    return build_interactive_summary(rows, reference)
