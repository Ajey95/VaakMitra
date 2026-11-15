"""Streaks & daily practice router.

Tracks consecutive-day practice. A "practice day" is any day the user completed
at least one evaluation. Drives the streak flame + weekly calendar heatmap.
"""
from fastapi import APIRouter, Depends
from typing import List
from datetime import timedelta
from ..database import get_database
from ..utils.jwt_handler import get_current_user, resolve_user_id
from ..utils.mongo import now

router = APIRouter(prefix="/api/streaks", tags=["streaks"])


async def _practice_days(user_id: str, days: int = 60) -> set:
    db = get_database()
    since = now() - timedelta(days=days)
    evals = await db.evaluations.find(
        {"user_id": user_id, "created_at": {"$gte": since}}, {"created_at": 1}
    ).to_list(length=100000)
    return {e["created_at"].date() for e in evals}


def _current_streak(day_set: set) -> int:
    streak, cursor = 0, now().date()
    # Allow today to be missing (streak still counts if practised yesterday).
    if cursor not in day_set:
        cursor = cursor - timedelta(days=1)
    while cursor in day_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _longest_streak(day_set: set) -> int:
    if not day_set:
        return 0
    days = sorted(day_set)
    longest = run = 1
    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    return longest


@router.get("")
async def my_streak(current_user: dict = Depends(get_current_user)):
    """Current streak, longest streak and total practice days."""
    day_set = await _practice_days(str(current_user["_id"]))
    return {
        "current_streak": _current_streak(day_set),
        "longest_streak": _longest_streak(day_set),
        "total_practice_days": len(day_set),
        "practiced_today": now().date() in day_set,
    }


@router.get("/heatmap")
async def heatmap(current_user: dict = Depends(get_current_user)):
    """Last-30-day practice heatmap (date -> practised bool + session count)."""
    db = get_database()
    uid = str(current_user["_id"])
    since = now() - timedelta(days=30)
    evals = await db.evaluations.find({"user_id": uid, "created_at": {"$gte": since}}, {"created_at": 1}).to_list(length=100000)
    counts = {}
    for e in evals:
        k = e["created_at"].strftime("%Y-%m-%d")
        counts[k] = counts.get(k, 0) + 1
    grid = []
    for i in range(29, -1, -1):
        d = (now() - timedelta(days=i)).strftime("%Y-%m-%d")
        grid.append({"date": d, "count": counts.get(d, 0), "practiced": counts.get(d, 0) > 0})
    return {"heatmap": grid}


@router.get("/{user_id}")
async def user_streak(user_id: str, current_user: dict = Depends(get_current_user)):
    """Streak for a specific user (self, or admin/therapist)."""
    target = resolve_user_id(current_user, user_id)
    day_set = await _practice_days(target)
    return {
        "current_streak": _current_streak(day_set),
        "longest_streak": _longest_streak(day_set),
        "total_practice_days": len(day_set),
    }
