"""Dashboard router — one-call aggregates for the user home screen.

Bundles the numbers the dashboard needs (wallet, streak, today's activity,
unread counts, next appointment) so the client makes a single request.
"""
from fastapi import APIRouter, Depends
from datetime import timedelta
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, now

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/home")
async def home(current_user: dict = Depends(get_current_user)):
    """Everything the home screen shows, in one payload."""
    db = get_database()
    uid = str(current_user["_id"])
    start = now().replace(hour=0, minute=0, second=0, microsecond=0)

    wallet = await db.wallets.find_one({"user_id": uid}) or {"coins": 0, "gems": 0, "level": 1}
    unread_notifs = await db.notifications.count_documents({"user_id": uid, "read": False})
    next_appt = await db.appointments.find_one(
        {"user_id": uid, "status": {"$in": ["pending", "confirmed"]}, "scheduled_at": {"$gte": now()}},
        sort=[("scheduled_at", 1)],
    )
    sessions_today = await db.evaluations.count_documents({"user_id": uid, "created_at": {"$gte": start}})

    return {
        "greeting_name": current_user.get("child_name") or current_user.get("full_name"),
        "stats": {
            "total_sessions": current_user.get("total_sessions", 0),
            "total_stars": current_user.get("total_stars", 0),
            "sessions_today": sessions_today,
        },
        "wallet": {"coins": wallet.get("coins", 0), "gems": wallet.get("gems", 0), "level": wallet.get("level", 1)},
        "unread_notifications": unread_notifs,
        "next_appointment": serialize(next_appt),
    }


@router.get("/quick-stats")
async def quick_stats(current_user: dict = Depends(get_current_user)):
    """Small stat tiles: 7-day sessions, avg accuracy, lessons completed."""
    db = get_database()
    uid = str(current_user["_id"])
    week_ago = now() - timedelta(days=7)
    week_sessions = await db.evaluations.count_documents({"user_id": uid, "created_at": {"$gte": week_ago}})
    evals = await db.evaluations.find({"user_id": uid}, {"accuracy": 1}).sort("created_at", -1).limit(20).to_list(length=20)
    avg = round(sum(e.get("accuracy", 0) for e in evals) / len(evals), 1) if evals else 0
    lessons = await db.progress.count_documents({"user_id": uid, "completed": True})
    return {"sessions_7d": week_sessions, "recent_avg_accuracy": avg, "lessons_completed": lessons}


@router.get("/leaderboard-preview")
async def leaderboard_preview(current_user: dict = Depends(get_current_user)):
    """Top-3 global leaderboard preview + the caller's own rank, for the home card."""
    db = get_database()
    uid = str(current_user["_id"])
    top = await db.users.find({"role": "user"}, {"child_name": 1, "total_stars": 1}).sort("total_stars", -1).limit(3).to_list(length=3)
    my_stars = current_user.get("total_stars", 0)
    my_rank = await db.users.count_documents({"role": "user", "total_stars": {"$gt": my_stars}}) + 1
    return {
        "top3": [{"rank": i + 1, "name": u.get("child_name") or "Learner", "stars": u.get("total_stars", 0)} for i, u in enumerate(top)],
        "my_rank": my_rank,
        "my_stars": my_stars,
    }


@router.get("/whats-new")
async def whats_new(current_user: dict = Depends(get_current_user)):
    """Latest announcement + active challenges count for a 'what's new' card."""
    db = get_database()
    latest = await db.announcements.find_one({"published": True}, sort=[("created_at", -1)])
    challenges = await db.challenges.count_documents({"active": True})
    polls = await db.polls.count_documents({"active": True})
    return {"latest_announcement": serialize(latest), "active_challenges": challenges, "active_polls": polls}
