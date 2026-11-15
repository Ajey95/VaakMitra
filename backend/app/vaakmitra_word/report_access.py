"""RPT-004/007: independently verified, purpose-bound therapist report access."""

import re
from datetime import datetime, timezone

SHA256 = re.compile(r"^[a-f0-9]{64}$")


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


async def report_share_allowed(db, child_id: str, therapist_id: str) -> bool:
    """RPT-007: absent, malformed, expired, withdrawn or unverified grant means no access."""
    latest = await db.report_share_grants.find_one(
        {"child_id": child_id}, sort=[("created_at", -1), ("_id", -1)],
    )
    if not latest or not isinstance(latest.get("created_at"), datetime):
        return False
    verified_at, valid_until = latest.get("verified_at"), latest.get("valid_until")
    return bool(
        latest.get("status") == "verified"
        and latest.get("purpose") == "word_session_report"
        and latest.get("therapist_id") == therapist_id
        and latest.get("submitted_by") == child_id
        and latest.get("verified_by") not in (None, child_id)
        and latest.get("guardian_relationship_verified") is True
        and isinstance(latest.get("guardian_evidence_sha256"), str)
        and SHA256.fullmatch(latest["guardian_evidence_sha256"])
        and isinstance(verified_at, datetime)
        and isinstance(valid_until, datetime)
        and utc(verified_at) <= datetime.now(timezone.utc) < utc(valid_until)
        and latest.get("withdrawn_at") is None
    )
