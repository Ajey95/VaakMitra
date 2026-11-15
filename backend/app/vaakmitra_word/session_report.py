"""RPT-001/002: bounded, provenance-preserving word-session report projection."""

from collections import Counter
from datetime import datetime, timezone

TIMELINE_FIELDS = (
    "word_id", "decision", "reason_code", "response_intent", "avatar_state",
    "model_version", "classifier_version", "reference_bank_version",
    "calibration_version", "policy_version",
)
VALID_DECISIONS = frozenset({"PASS", "RETRY", "UNSCORABLE"})


def build_session_summary(session: dict) -> dict:
    attempts = session.get("attempts") or []
    planned = session.get("word_ids") or []
    if len(attempts) > 60 or len(planned) > 25:
        raise ValueError("session_report_limit_exceeded")
    if any(not isinstance(row, dict) or row.get("decision") not in VALID_DECISIONS
           or row.get("word_id") not in planned for row in attempts):
        raise ValueError("session_report_invalid_attempt")

    timeline = [
        {"ordinal": index + 1, **{key: row[key] for key in TIMELINE_FIELDS if key in row}}
        for index, row in enumerate(attempts)
    ]
    counts = Counter(row["decision"] for row in attempts)
    scoreable_words = {}
    eventual_pass_words = set()
    for row in attempts:
        word_id, decision = row["word_id"], row["decision"]
        if decision in ("PASS", "RETRY"):
            scoreable_words.setdefault(word_id, decision)
        if decision == "PASS":
            eventual_pass_words.add(word_id)

    total_captures = session.get("total_attempts", 0)
    if not isinstance(total_captures, int) or total_captures < 0:
        raise ValueError("session_report_invalid_capture_count")
    incomplete = total_captures - len(attempts)
    raw_events = session.get("session_events")
    events = raw_events[:120] if isinstance(raw_events, list) else []
    metrics = {
        "planned_words": len(planned),
        "attempted_words": len({row["word_id"] for row in attempts}),
        "scoreable_words": len(scoreable_words),
        "first_scoreable_pass_words": sum(decision == "PASS" for decision in scoreable_words.values()),
        "eventual_pass_words": len(eventual_pass_words),
        "total_captures": total_captures,
        "completed_attempts": len(attempts),
        "captures_without_completion": incomplete if incomplete >= 0 else None,
        "scoreable_attempts": counts["PASS"] + counts["RETRY"],
        "retry_attempts": counts["RETRY"],
        "unscorable_attempts": counts["UNSCORABLE"],
        "voluntary_breaks": sum(isinstance(event, dict) and event.get("type") == "break_started"
                                and event.get("reason") == "user_pause" for event in events),
    }
    started = session.get("created_at")
    session_events = []
    for event in events:
        if not isinstance(event, dict) or event.get("type") not in {
            "break_started", "break_ended", "session_resumed", "session_ended",
        }:
            continue
        at = event.get("at")
        if isinstance(started, datetime) and isinstance(at, datetime):
            start_utc = started.replace(tzinfo=timezone.utc) if started.tzinfo is None else started
            at_utc = at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at
            second = round((at_utc - start_utc).total_seconds())
        else:
            second = None
        session_events.append({"type": event["type"], "reason": event.get("reason"),
                               "session_second": max(0, second) if second is not None else None})
    return {
        "schema_version": "word-session-report-1",
        "session_id": session["_id"],
        "status": session["status"],
        "plan_id": session.get("plan_id"),
        "vocabulary_version": session.get("vocabulary_version"),
        "total_captures": total_captures,
        "completed_attempts": len(attempts),
        "decisions": {decision: counts[decision] for decision in ("PASS", "RETRY", "UNSCORABLE")},
        "metrics": metrics,
        "timeline": timeline,
        "session_events": session_events,
        "break_data_status": "recorded" if isinstance(raw_events, list) else "unavailable_legacy",
    }
