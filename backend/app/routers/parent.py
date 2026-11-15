"""Parent portal: a weekly rollup of the child's practice for the logged-in parent."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends

from ..database import get_database
from ..utils.jwt_handler import get_current_user
from .analysis import summarize_evaluations


router = APIRouter(prefix="/api/parent", tags=["parent"])


def weekly_rollup(evaluations: List[Dict], now: datetime) -> Dict:
    """Compute this-week vs previous-week stats from evaluation docs.

    Pure function (testable): `evaluations` each need accuracy, stars_earned,
    created_at (datetime). `now` is the reference time.
    """
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    this_week = [e for e in evaluations if e.get("created_at") and e["created_at"] >= week_ago]
    prev_week = [
        e for e in evaluations
        if e.get("created_at") and two_weeks_ago <= e["created_at"] < week_ago
    ]

    def avg_acc(evs):
        accs = [e.get("accuracy", 0) for e in evs]
        return round(sum(accs) / len(accs), 1) if accs else 0.0

    this_acc = avg_acc(this_week)
    prev_acc = avg_acc(prev_week)
    return {
        "sessions_this_week": len(this_week),
        "stars_this_week": sum(e.get("stars_earned", 0) for e in this_week),
        "avg_accuracy_this_week": this_acc,
        "avg_accuracy_prev_week": prev_acc,
        "accuracy_delta": round(this_acc - prev_acc, 1),
        "active_days_this_week": len({
            e["created_at"].date() for e in this_week if e.get("created_at")
        }),
    }


@router.get("/weekly")
async def parent_weekly(current_user: dict = Depends(get_current_user)):
    """Weekly summary + overall analytics for the current parent's child."""
    db = get_database()
    user_id = str(current_user["_id"])
    evaluations = await db.evaluations.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(300).to_list(length=300)

    rollup = weekly_rollup(evaluations, datetime.utcnow())
    analysis = summarize_evaluations(evaluations)

    # A simple, honest recommendation for the parent.
    recommendation: Optional[str] = None
    if not evaluations:
        recommendation = "Start your child's first practice session to begin tracking progress."
    elif analysis["weakest"]:
        w = analysis["weakest"]
        recommendation = (
            f"Practice '{w['phoneme']}' together — it's currently the lowest at "
            f"{round(w['accuracy'])}%. Short daily sessions help most."
        )

    return {
        "child_name": current_user.get("child_name"),
        "weekly": rollup,
        "overall": analysis,
        "recommendation": recommendation,
    }
