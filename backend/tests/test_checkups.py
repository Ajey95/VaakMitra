"""DEC-019/CHK-001..003: fortnightly status never fabricates a visit."""

from datetime import datetime, timedelta, timezone

from app.vaakmitra_word.checkups import checkup_status


START = datetime(2026, 9, 1, 10, tzinfo=timezone.utc)
THERAPIST_ID = "therapist-a"


def test_chk001_unknown_assignment_never_invents_due_date():
    assert checkup_status(None, None, [], START) == {
        "state": "therapist_unassigned", "due_at": None, "practice_available": True,
        "appointment": None,
    }
    assert checkup_status(THERAPIST_ID, None, [], START)["state"] == "schedule_unestablished"
    assert checkup_status(THERAPIST_ID, None, [], START)["due_at"] is None


def test_chk001_legacy_assignment_gets_clock_only_after_real_therapist_completion():
    rows = [{"kind": "checkup", "status": "completed", "therapist_id": THERAPIST_ID,
             "completed_by": THERAPIST_ID, "completed_at": START}]
    result = checkup_status(THERAPIST_ID, None, rows, START + timedelta(days=1))
    assert result["state"] == "not_due"
    assert result["due_at"] == "2026-09-15T10:00:00+00:00"


def test_chk001_due_exactly_14_days_after_assignment():
    before = checkup_status(THERAPIST_ID, START, [], START + timedelta(days=14, seconds=-1))
    due = checkup_status(THERAPIST_ID, START, [], START + timedelta(days=14))
    late = checkup_status(THERAPIST_ID, START, [], START + timedelta(days=15))
    assert before["state"] == "not_due"
    assert due["state"] == "due"
    assert late["state"] == "overdue"
    assert due["due_at"] == "2026-09-15T10:00:00+00:00"
    assert late["practice_available"] is True


def test_chk001_only_assigned_therapist_completed_checkup_resets_clock():
    rows = [
        {"kind": "ordinary", "status": "completed", "therapist_id": THERAPIST_ID, "completed_at": START + timedelta(days=10), "completed_by": THERAPIST_ID},
        {"kind": "checkup", "status": "completed", "therapist_id": THERAPIST_ID, "completed_at": START + timedelta(days=11), "completed_by": "other-therapist"},
        {"kind": "checkup", "status": "cancelled", "therapist_id": THERAPIST_ID, "completed_at": START + timedelta(days=12), "completed_by": THERAPIST_ID},
        {"kind": "checkup", "status": "completed", "therapist_id": THERAPIST_ID, "completed_at": START + timedelta(days=13), "completed_by": THERAPIST_ID},
    ]
    result = checkup_status(THERAPIST_ID, START, rows, START + timedelta(days=14))
    assert result["state"] == "not_due"
    assert result["due_at"] == "2026-09-28T10:00:00+00:00"


def test_chk003_pending_request_does_not_reset_due_clock():
    rows = [{"kind": "checkup", "status": "pending", "scheduled_at": START + timedelta(days=17),
             "therapist_id": THERAPIST_ID}]
    result = checkup_status(THERAPIST_ID, START, rows, START + timedelta(days=16))
    assert result["state"] == "overdue"
    assert result["appointment"]["status"] == "pending"
    assert result["practice_available"] is True
