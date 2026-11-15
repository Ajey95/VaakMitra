"""Speech analytics derived from stored evaluations.

Powers the Speech Analysis page and the Reports detail tabs. `summarize_evaluations`
is a pure function over evaluation dicts and is unit-tested directly.
"""
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends

from ..database import get_database
from ..utils.jwt_handler import get_current_user, resolve_user_id


router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _avg(values: List[float]) -> float:
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def summarize_evaluations(evaluations: List[Dict]) -> Dict:
    """Aggregate a list of evaluation docs into analytics for the UI.

    Each evaluation is expected to have: accuracy, gop_score, mfcc_score,
    airflow_score, phoneme, weakest_syllable, created_at (datetime).
    Evaluations should be passed newest-first; history is returned oldest-first.
    """
    if not evaluations:
        return {
            "has_data": False,
            "total_attempts": 0,
            "overall": 0.0,
            "best_accuracy": 0.0,
            "metrics": {"accuracy": 0.0, "clarity": 0.0, "sound_match": 0.0, "airflow": 0.0},
            "by_phoneme": [],
            "history": [],
            "weakest": None,
        }

    accuracies = [e.get("accuracy", 0) for e in evaluations]
    metrics = {
        "accuracy": _avg(accuracies),
        "clarity": _avg([e.get("gop_score", 0) for e in evaluations]),
        "sound_match": _avg([e.get("mfcc_score", 0) for e in evaluations]),
        "airflow": _avg([(e.get("airflow_score", 0) or 0) * 100 for e in evaluations]),
    }

    # Per-phoneme aggregates
    groups: Dict[str, List[Dict]] = {}
    for e in evaluations:
        groups.setdefault(e.get("phoneme") or "?", []).append(e)
    by_phoneme = []
    for phoneme, evs in groups.items():
        by_phoneme.append({
            "phoneme": phoneme,
            "accuracy": _avg([e.get("accuracy", 0) for e in evs]),
            "gop": _avg([e.get("gop_score", 0) for e in evs]),
            "attempts": len(evs),
        })
    by_phoneme.sort(key=lambda p: p["accuracy"], reverse=True)

    # History (oldest-first) for the trend chart, last 10 attempts
    recent = list(reversed(evaluations[:10]))
    history = []
    for e in recent:
        created = e.get("created_at")
        label = created.strftime("%m/%d") if hasattr(created, "strftime") else ""
        history.append({"label": label, "accuracy": round(e.get("accuracy", 0), 1)})

    weakest = min(by_phoneme, key=lambda p: p["accuracy"]) if by_phoneme else None

    return {
        "has_data": True,
        "total_attempts": len(evaluations),
        "overall": metrics["accuracy"],
        "best_accuracy": round(max(accuracies), 1),
        "metrics": metrics,
        "by_phoneme": by_phoneme,
        "history": history,
        "weakest": weakest,
    }


@router.get("/{user_id}")
async def get_analysis(user_id: str, current_user: dict = Depends(get_current_user)):
    """Return speech analytics for a user, computed from stored evaluations."""
    user_id = resolve_user_id(current_user, user_id)
    db = get_database()
    evaluations = await db.evaluations.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(200).to_list(length=200)
    return summarize_evaluations(evaluations)
