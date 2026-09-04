"""Therapist ingest must be retry-safe across device retransmissions."""

import pytest
from sqlalchemy import func, select

from asd_backend.config import settings
from asd_backend.db.models import AuditEvent


@pytest.mark.asyncio
async def test_duplicate_idempotency_key_is_acknowledged_once(api_client, test_db):
    payload = {
        "pseudonym_id": "child-pseudo-1",
        "session_id": "session-1",
        "attempt_id": "attempt-1",
        "exercise_id": "TA_AMMA_01",
        "overall_pass": True,
        "syllable_scores_aggregate": {"pass_count": 2, "total_count": 2},
        "model_version": "ta-ctc-1",
        "dict_version": "ta-dict-1",
        "policy_version": "policy-1",
        "consent_version": "consent-1",
        "timestamp_utc": "2026-09-04T00:00:00+00:00",
    }
    headers = {
        "Authorization": f"Bearer {settings.sync_api_token}",
        "X-Idempotency-Key": "attempt-attempt-1",
    }
    first = await api_client.post("/therapist/ingest", json=payload, headers=headers)
    duplicate = await api_client.post("/therapist/ingest", json=payload, headers=headers)

    assert first.status_code == 200
    assert first.json()["received_count"] == 1
    assert duplicate.status_code == 200
    assert duplicate.json()["received_count"] == 0
    count = await test_db.scalar(
        select(func.count(AuditEvent.event_id)).where(
            AuditEvent.event_type == "sync_received"
        )
    )
    assert count == 1
