"""DEC-019/CHK-001..003: deterministic 14-day therapist checkup clock."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def checkup_status(
    therapist_id: str | None,
    assigned_at: datetime | None,
    appointments: list[dict],
    at: datetime,
) -> dict:
    """Return a caregiver reminder; appointment requests never reset the due clock."""
    base = {"state": "therapist_unassigned", "due_at": None,
            "practice_available": True, "appointment": None}
    if not therapist_id:
        return base
    active = [row for row in appointments if row.get("kind") == "checkup"
              and row.get("therapist_id") == therapist_id
              and row.get("status") in {"pending", "confirmed"}]
    if active:
        selected = min(active, key=lambda row: _utc(row["scheduled_at"]))
        base["appointment"] = {
            "id": str(selected.get("_id")) if selected.get("_id") else None,
            "status": selected["status"],
            "scheduled_at": _utc(selected["scheduled_at"]).isoformat(),
        }
    anchor = _utc(assigned_at) if assigned_at is not None else None
    for row in appointments:
        completed = row.get("completed_at")
        if (row.get("kind") == "checkup" and row.get("status") == "completed"
                and row.get("therapist_id") == therapist_id
                and row.get("completed_by") == therapist_id
                and isinstance(completed, datetime)
                and (anchor is None or _utc(completed) >= anchor)):
            anchor = max(anchor, _utc(completed)) if anchor is not None else _utc(completed)
    if anchor is None:
        base["state"] = "schedule_unestablished"
        return base
    due = anchor + timedelta(days=14)
    current = _utc(at)
    base["due_at"] = due.isoformat()
    base["state"] = "not_due" if current < due else "due" if current == due else "overdue"
    return base
