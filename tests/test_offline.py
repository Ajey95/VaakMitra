"""
Offline / airplane mode tests — M3.5

Verifies that:
1. Therapy session completes when the sync server is unavailable.
2. Metrics are queued (not lost) when offline.
3. The sync queue drains correctly when the server comes back online.
"""

from __future__ import annotations

import asyncio
import base64
import json

import pytest

from asd_backend.adaptive.policy import TherapistPolicy
from asd_backend.db.repositories import (
    ChildProfileRepository,
    ExercisePlanRepository,
    SyncQueueRepository,
)
from asd_backend.session.orchestrator import SessionOrchestrator
from asd_backend.session.schemas import SessionStartRequest
from asd_backend.sync.allow_list import build_sync_payload
from asd_backend.sync.service import SyncService
from tests.conftest import _use_test_engine
import asd_backend.db.database as _db_module

SAMPLE_EXERCISES = [
    {
        "id": "TA_AMMA_01",
        "target_word": "அம்மா",
        "target_phonemes": ["a", "m", "m", "a:"],
        "syllables": ["அம்", "மா"],
        "difficulty": "easy",
    }
]


async def _seed(test_db):
    child_repo = ChildProfileRepository(test_db)
    await child_repo.create("child-offline-test", consent_version="1.0")
    plan_repo = ExercisePlanRepository(test_db)
    plan = await plan_repo.create(
        therapist_ref="test-therapist",
        policy_version="0.0.1-dev",
        plan_version="1.0.0",
        exercises=SAMPLE_EXERCISES,
    )
    await test_db.commit()
    return "child-offline-test", plan.plan_id


# ---------------------------------------------------------------------------
# Offline: session continues without network
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_session_completes_offline(test_db, test_engine):
    """
    A full therapy session must complete successfully even when the
    sync server is completely unreachable.
    """
    await _use_test_engine(test_engine)

    pseudonym_id, plan_id = await _seed(test_db)
    orch = SessionOrchestrator(policy=TherapistPolicy.default())

    start_resp = await orch.start_session(
        SessionStartRequest(pseudonym_id=pseudonym_id, plan_id=plan_id)
    )

    audio_b64 = base64.b64encode(bytes(16000 * 2)).decode()
    result = await orch.submit_attempt(
        session_id=start_resp.session_id,
        exercise_id="TA_AMMA_01",
        target_word="அம்மா",
        audio_b64=audio_b64,
    )

    # Session must produce a valid result regardless of network state
    assert result.result in {"pass", "targeted_coaching", "retry", "break", "no_response"}
    assert result.session_id == start_resp.session_id

    end_resp = await orch.end_session(start_resp.session_id)
    assert end_resp.status == "completed"


# ---------------------------------------------------------------------------
# Offline: metrics are queued, not lost
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metrics_queued_when_offline(test_db, test_engine):
    """
    When the sync server is offline, metrics must be stored in the
    sync queue and not dropped.
    """
    await _use_test_engine(test_engine)

    # Directly enqueue a packet
    async with _db_module.AsyncSessionLocal() as db:
        repo = SyncQueueRepository(db)
        payload = build_sync_payload(
            pseudonym_id="child-offline-test",
            session_id="SES-OFFLINE",
            attempt_id="ATT-OFFLINE-01",
            exercise_id="TA_AMMA_01",
            syllable_scores=[{"syllable": "அம்", "score": 0.9, "status": "pass"}],
            overall_pass=True,
            model_version="stub",
            dict_version="ta-dict-1.0.0",
            policy_version="1.0.0",
        )
        await repo.enqueue(idempotency_key="attempt-ATT-OFFLINE-01", payload=payload)
        await db.commit()

    # Point sync to an unreachable server
    sync_service = SyncService(
        base_url="http://127.0.0.1:19999",  # nothing listening here
        api_token="test",
        max_retries=0,
        timeout_s=0.5,
    )
    sent = await sync_service.run_once()

    # Nothing sent (offline) but queue entry must still be pending
    assert sent == 0

    async with _db_module.AsyncSessionLocal() as db:
        repo = SyncQueueRepository(db)
        pending = await repo.pending()
        assert len(pending) >= 1, "Metric was lost from queue when offline!"


# ---------------------------------------------------------------------------
# Queue drains when server comes back (mock server)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_queue_drains_when_server_available(test_db, test_engine):
    """
    Once the server is reachable, the pending queue must drain successfully.
    """
    from asd_backend.sync.mock_server import MockTherapistServer
    await _use_test_engine(test_engine)

    # Start mock therapist server
    server = MockTherapistServer(port=9098)
    server.start()

    try:
        # Enqueue a packet
        async with _db_module.AsyncSessionLocal() as db:
            repo = SyncQueueRepository(db)
            payload = build_sync_payload(
                pseudonym_id="child-drain-test",
                session_id="SES-DRAIN",
                attempt_id="ATT-DRAIN-01",
                exercise_id="TA_AMMA_01",
                syllable_scores=[{"syllable": "அம்", "score": 0.88, "status": "pass"}],
                overall_pass=True,
                model_version="stub",
                dict_version="ta-dict-1.0.0",
                policy_version="1.0.0",
            )
            await repo.enqueue(idempotency_key="attempt-ATT-DRAIN-01", payload=payload)
            await db.commit()

        # Run sync against mock server
        sync_service = SyncService(
            base_url=server.base_url,
            api_token="test",
            timeout_s=5.0,
        )
        sent = await sync_service.run_once()

        # Packet must have been sent
        assert sent == 1
        assert len(server.received_packets) == 1

        # Verify the received packet has no forbidden fields
        received = server.received_packets[0]
        received_str = json.dumps(received).lower()
        assert "audio" not in received_str
        assert "mfcc" not in received_str
        assert "embedding" not in received_str
        assert "gop" not in received_str

    finally:
        server.stop()
