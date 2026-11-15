"""Analysis extras — phoneme drill-down, recommendations and comparisons.

Extends the analysis router with deeper per-phoneme insight used by the Speech
Analysis page.
"""
from fastapi import APIRouter, Depends
from datetime import timedelta
from ..database import get_database
from ..utils.jwt_handler import get_current_user, resolve_user_id
from ..utils.mongo import now

router = APIRouter(prefix="/api/analysis", tags=["analysis-ext"])


@router.get("/phoneme/{user_id}/{phoneme}")
async def phoneme_detail(user_id: str, phoneme: str, current_user: dict = Depends(get_current_user)):
    """Trend + averages for a single phoneme."""
    target = resolve_user_id(current_user, user_id)
    db = get_database()
    evals = await db.evaluations.find({"user_id": target, "phoneme": phoneme}).sort("created_at", 1).to_list(length=1000)
    trend = [{"date": e["created_at"].strftime("%Y-%m-%d"), "accuracy": e.get("accuracy", 0)} for e in evals]
    accs = [e.get("accuracy", 0) for e in evals]
    return {
        "phoneme": phoneme, "attempts": len(evals),
        "avg_accuracy": round(sum(accs) / len(accs), 1) if accs else 0,
        "best": max(accs) if accs else 0, "latest": accs[-1] if accs else 0, "trend": trend,
    }


@router.get("/recommendations/{user_id}")
async def recommendations(user_id: str, current_user: dict = Depends(get_current_user)):
    """Rank phonemes by weakness and suggest what to practise next."""
    target = resolve_user_id(current_user, user_id)
    db = get_database()
    evals = await db.evaluations.find({"user_id": target}).to_list(length=100000)
    by_phoneme = {}
    for e in evals:
        by_phoneme.setdefault(e.get("phoneme", "?"), []).append(e.get("accuracy", 0))
    ranked = sorted(
        [{"phoneme": p, "avg": round(sum(v) / len(v), 1), "attempts": len(v)} for p, v in by_phoneme.items()],
        key=lambda x: x["avg"],
    )
    recs = [{"phoneme": r["phoneme"], "reason": f"Average {r['avg']}% over {r['attempts']} tries — needs practice"} for r in ranked[:3]]
    return {"weakest": ranked[:5], "strongest": ranked[-5:][::-1], "recommendations": recs}


@router.get("/consistency/{user_id}")
async def consistency(user_id: str, current_user: dict = Depends(get_current_user)):
    """Practice consistency over the last 30 days (active days, gaps)."""
    target = resolve_user_id(current_user, user_id)
    db = get_database()
    since = now() - timedelta(days=30)
    evals = await db.evaluations.find({"user_id": target, "created_at": {"$gte": since}}, {"created_at": 1}).to_list(length=100000)
    days = {e["created_at"].date() for e in evals}
    return {"active_days_30d": len(days), "consistency_pct": round(len(days) / 30 * 100, 1), "total_sessions_30d": len(evals)}


@router.get("/skill-radar/{user_id}")
async def skill_radar(user_id: str, current_user: dict = Depends(get_current_user)):
    """Radar-chart data: average of each sub-metric (clarity, match, airflow)."""
    target = resolve_user_id(current_user, user_id)
    db = get_database()
    evals = await db.evaluations.find({"user_id": target}).to_list(length=100000)
    if not evals:
        return {"radar": []}
    n = len(evals)
    return {"radar": [
        {"axis": "Accuracy", "value": round(sum(e.get("accuracy", 0) for e in evals) / n, 1)},
        {"axis": "Clarity (GOP)", "value": round(sum(e.get("gop_score", 0) for e in evals) / n, 1)},
        {"axis": "Sound Match (MFCC)", "value": round(sum(e.get("mfcc_score", 0) for e in evals) / n, 1)},
        {"axis": "Airflow", "value": round(sum(e.get("airflow_score", 0) * 100 for e in evals) / n, 1)},
    ]}
