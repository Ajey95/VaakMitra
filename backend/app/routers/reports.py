"""Reports router — build, save and export analytical reports.

Backs the Reports page. Users/therapists/admins build reports over data sources
(sessions, accuracy, quizzes, games), render totals + chart data, save report
definitions, and export CSV.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import csv
import io
from ..database import get_database
from ..utils.jwt_handler import get_current_user, resolve_user_id
from ..utils.mongo import serialize, paginate, oid, now

router = APIRouter(prefix="/api/reports", tags=["reports"])

SOURCES = ["sessions", "accuracy", "quizzes", "games", "progress"]
GROUP_BY = ["day", "week", "month", "lesson", "phoneme", "type"]


class ReportDefinition(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source: str
    group_by: str = "week"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


def _bucket_key(dt: datetime, group_by: str) -> str:
    if group_by == "day":
        return dt.strftime("%Y-%m-%d")
    if group_by == "week":
        return f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
    if group_by == "month":
        return dt.strftime("%Y-%m")
    return dt.strftime("%Y-%m-%d")


async def _build(user_id: str, source: str, group_by: str, date_from, date_to) -> dict:
    db = get_database()
    date_from = date_from or (now() - timedelta(days=90))
    date_to = date_to or now()

    rows, measure_label = [], "count"
    if source in ("sessions", "accuracy"):
        evals = await db.evaluations.find(
            {"user_id": user_id, "created_at": {"$gte": date_from, "$lte": date_to}}
        ).to_list(length=100000)
        buckets = {}
        for e in evals:
            key = _bucket_key(e["created_at"], group_by) if group_by in ("day", "week", "month") else str(e.get("phoneme") if group_by == "phoneme" else e.get("lesson_id"))
            buckets.setdefault(key, [])
            buckets[key].append(e.get("accuracy", 0))
        if source == "accuracy":
            measure_label = "avg_accuracy"
            rows = [{"group": k, "value": round(sum(v) / len(v), 1) if v else 0, "count": len(v)} for k, v in buckets.items()]
        else:
            measure_label = "sessions"
            rows = [{"group": k, "value": len(v), "count": len(v)} for k, v in buckets.items()]
    elif source == "quizzes":
        attempts = await db.quiz_attempts.find(
            {"user_id": user_id, "created_at": {"$gte": date_from, "$lte": date_to}}
        ).to_list(length=100000)
        buckets = {}
        for a in attempts:
            key = _bucket_key(a["created_at"], group_by) if group_by in ("day", "week", "month") else str(a.get("type"))
            buckets.setdefault(key, []).append(a.get("score_pct", 0))
        measure_label = "avg_score"
        rows = [{"group": k, "value": round(sum(v) / len(v), 1) if v else 0, "count": len(v)} for k, v in buckets.items()]
    elif source == "games":
        scores = await db.game_scores.find(
            {"user_id": user_id, "created_at": {"$gte": date_from, "$lte": date_to}}
        ).to_list(length=100000)
        buckets = {}
        for s in scores:
            key = _bucket_key(s["created_at"], group_by) if group_by in ("day", "week", "month") else str(s.get("game_slug"))
            buckets.setdefault(key, []).append(s.get("score", 0))
        measure_label = "total_score"
        rows = [{"group": k, "value": sum(v), "count": len(v)} for k, v in buckets.items()]
    elif source == "progress":
        prog = await db.progress.find({"user_id": user_id}).to_list(length=100000)
        measure_label = "best_accuracy"
        rows = [{"group": f"lesson-{p.get('lesson_id')}", "value": p.get("best_accuracy", 0), "count": p.get("attempts", 0)} for p in prog]

    rows.sort(key=lambda r: r["group"])
    total = sum(r["value"] for r in rows)
    return {
        "source": source, "group_by": group_by, "measure": measure_label,
        "rows": rows, "total": round(total, 1), "row_count": len(rows),
        "date_from": date_from.isoformat(), "date_to": date_to.isoformat(),
    }


@router.get("/meta")
async def report_meta(current_user: dict = Depends(get_current_user)):
    """Available sources and group-by options for the report builder."""
    return {"sources": SOURCES, "group_by": GROUP_BY}


@router.post("/run")
async def run_report(payload: ReportDefinition, current_user: dict = Depends(get_current_user)):
    """Build and return a report for the current user (no persistence)."""
    if payload.source not in SOURCES:
        raise HTTPException(status_code=400, detail="Invalid source")
    return await _build(str(current_user["_id"]), payload.source, payload.group_by, payload.date_from, payload.date_to)


@router.post("/run/{user_id}")
async def run_report_for(user_id: str, payload: ReportDefinition, current_user: dict = Depends(get_current_user)):
    """Build a report for a specific user (self, or admin/therapist for others)."""
    target = resolve_user_id(current_user, user_id)
    return await _build(target, payload.source, payload.group_by, payload.date_from, payload.date_to)


@router.post("/save")
async def save_report(payload: ReportDefinition, current_user: dict = Depends(get_current_user)):
    """Save a report definition for later re-runs."""
    db = get_database()
    doc = {"user_id": str(current_user["_id"]), **payload.model_dump(), "created_at": now()}
    result = await db.saved_reports.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/saved")
async def list_saved(current_user: dict = Depends(get_current_user)):
    """List the caller's saved report definitions."""
    db = get_database()
    rows = await db.saved_reports.find({"user_id": str(current_user["_id"])}).sort("created_at", -1).to_list(length=200)
    return {"reports": serialize(rows)}


@router.delete("/saved/{report_id}")
async def delete_saved(report_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a saved report definition."""
    db = get_database()
    result = await db.saved_reports.delete_one({"_id": oid(report_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"message": "Deleted"}


@router.post("/export")
async def export_report(payload: ReportDefinition, current_user: dict = Depends(get_current_user)):
    """Export a built report as CSV (formula-injection guarded)."""
    report = await _build(str(current_user["_id"]), payload.source, payload.group_by, payload.date_from, payload.date_to)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Group", report["measure"], "Count"])

    def guard(val):
        s = str(val)
        return "'" + s if s and s[0] in ("=", "+", "-", "@") else s

    for r in report["rows"]:
        writer.writerow([guard(r["group"]), r["value"], r["count"]])
    writer.writerow(["TOTAL", report["total"], ""])
    content = output.getvalue()
    output.close()
    return Response(
        content=content, media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{payload.source}_{now().strftime('%Y%m%d')}.csv"},
    )
