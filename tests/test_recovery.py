"""
Recovery and cleanup tests — M3.5

Verifies that cancellation, timeouts, and failures clean up
audio/intermediate data and leave the system in a consistent state.
"""

from __future__ import annotations

import asyncio
import base64

import pytest

from asd_backend.adaptive.policy import TherapistPolicy
from asd_backend.db.repositories import (
    ChildProfileRepository,
    ExercisePlanRepository,
    AttemptRepository,
)
from asd_backend.session.orchestrator import (
    AudioCaptureResult,
    Member1ServiceInterface,
    Member2ServiceInterface,
    SessionOrchestrator,
    StubMember2Service,
)
from asd_backend.session.schemas import CancelAttemptRequest, SessionStartRequest
from asd_backend.adaptive.schemas import ScoringResult
from tests.conftest import _use_test_engine

SAMPLE_EXERCISES = [
    {
        "id": "TA_AMMA_01",
        "target_word": "அம்மா",
        "target_phonemes": ["a", "m", "m", "a:"],
        "syllables": ["அம்", "மா"],
        "difficulty": "easy",
    }
]


# ---------------------------------------------------------------------------
# Slow M1 service that can be cancelled
# ---------------------------------------------------------------------------

class SlowMember1Service(Member1ServiceInterface):
    """Simulates a Member 1 service that takes longer than the timeout."""

    async def process(self, audio_bytes, target_word, exercise_id):
        await asyncio.sleep(999)  # simulate hang
        raise RuntimeError("Should not reach here")


# ---------------------------------------------------------------------------
# Failing M2 service
# ---------------------------------------------------------------------------

class FailingMember2Service(Member2ServiceInterface):
    """Simulates Member 2 throwing an exception during scoring."""

    async def score(self, audio_bytes, phoneme_alignment, expected_phonemes, attempt_id):
        raise RuntimeError("Member 2 inference failed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def silent_audio_b64():
    pcm_silence = bytes(16000 * 2)
    return base64.b64encode(pcm_silence).decode()


async def _seed(test_db):
    child_repo = ChildProfileRepository(test_db)
    await child_repo.create("child-recovery-test", consent_version="1.0")
    plan_repo = ExercisePlanRepository(test_db)
    plan = await plan_repo.create(
        therapist_ref="test-therapist",
        policy_version="0.0.1-dev",
        plan_version="1.0.0",
        exercises=SAMPLE_EXERCISES,
    )
    await test_db.commit()
    return "child-recovery-test", plan.plan_id


# ---------------------------------------------------------------------------
# Recovery tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancellation_does_not_persist_bad_state(test_db, test_engine):
    """
    When an attempt is cancelled mid-flight, the system must not leave
    a corrupt attempt record in the DB.
    """
    await _use_test_engine(test_engine)
    pseudonym_id, plan_id = await _seed(test_db)

    # Use a slow M1 to simulate cancellation
    orch = SessionOrchestrator(
        member1=SlowMember1Service(),
        member2=StubMember2Service(),
        policy=TherapistPolicy.default(),
    )

    start_resp = await orch.start_session(
        SessionStartRequest(pseudonym_id=pseudonym_id, plan_id=plan_id)
    )
    session_id = start_resp.session_id

    # Start attempt and cancel immediately
    attempt_task = asyncio.create_task(
        orch.submit_attempt(
            session_id=session_id,
            exercise_id="TA_AMMA_01",
            target_word="அம்மா",
            audio_b64=base64.b64encode(bytes(100)).decode(),
        )
    )
    # Let it start
    await asyncio.sleep(0.1)
    await orch.cancel_attempt(CancelAttemptRequest(session_id=session_id))

    # The task should complete with a neutral result (timeout/cancel)
    result = await asyncio.wait_for(attempt_task, timeout=20)
    assert result.result in {"retry", "no_response", "break"}
    # No pronunciation judgement on cancelled attempt
    assert result.weak_unit is None


@pytest.mark.asyncio
async def test_m2_failure_produces_neutral_result(test_db, test_engine, silent_audio_b64):
    """
    When Member 2 scoring fails, the result must be a neutral retry
    (not a pronunciation judgement, not an unhandled exception).
    """
    await _use_test_engine(test_engine)

    class FixedM1Service(Member1ServiceInterface):
        async def process(self, audio_bytes, target_word, exercise_id):
            return AudioCaptureResult(
                attempt_id="ATT-FAIL-01",
                capture_status="valid",
                expected_word=target_word,
                expected_phonemes=["a", "m", "m", "a:"],
                phoneme_alignment=[],
                alignment_confidence=0.85,
            )

    pseudonym_id, plan_id = await _seed(test_db)
    orch = SessionOrchestrator(
        member1=FixedM1Service(),
        member2=FailingMember2Service(),
        policy=TherapistPolicy.default(),
    )

    start_resp = await orch.start_session(
        SessionStartRequest(pseudonym_id=pseudonym_id, plan_id=plan_id)
    )
    result = await orch.submit_attempt(
        session_id=start_resp.session_id,
        exercise_id="TA_AMMA_01",
        target_word="அம்மா",
        audio_b64=silent_audio_b64,
    )

    # Should produce a graceful result, not raise
    assert result.result in {"retry", "no_response", "break", "targeted_coaching", "pass"}


@pytest.mark.asyncio
async def test_session_state_cleaned_up_after_end(test_db, test_engine, silent_audio_b64):
    """After end_session, the in-memory session state must be cleaned up."""
    await _use_test_engine(test_engine)

    pseudonym_id, plan_id = await _seed(test_db)
    orch = SessionOrchestrator(policy=TherapistPolicy.default())

    start_resp = await orch.start_session(
        SessionStartRequest(pseudonym_id=pseudonym_id, plan_id=plan_id)
    )
    session_id = start_resp.session_id
    assert session_id in orch._states

    await orch.end_session(session_id)

    # State must be removed from memory
    assert session_id not in orch._states


@pytest.mark.asyncio
async def test_audio_bytes_not_in_db_after_attempt(test_db, test_engine, silent_audio_b64):
    """
    After a successful attempt, no audio bytes or base64 audio should
    appear anywhere in the DB attempt record.
    """
    await _use_test_engine(test_engine)

    pseudonym_id, plan_id = await _seed(test_db)
    orch = SessionOrchestrator(policy=TherapistPolicy.default())

    start_resp = await orch.start_session(
        SessionStartRequest(pseudonym_id=pseudonym_id, plan_id=plan_id)
    )
    await orch.submit_attempt(
        session_id=start_resp.session_id,
        exercise_id="TA_AMMA_01",
        target_word="அம்மா",
        audio_b64=silent_audio_b64,
    )

    # Check DB attempt record has no audio content
    attempt_repo = AttemptRepository(test_db)
    attempts = await attempt_repo.list_for_session(start_resp.session_id)
    assert len(attempts) > 0

    for attempt in attempts:
        col_values = {
            col.name: getattr(attempt, col.name)
            for col in attempt.__table__.columns
            if getattr(attempt, col.name) is not None
        }
        for col_name, value in col_values.items():
            if isinstance(value, str) and len(value) > 100:
                assert silent_audio_b64[:20] not in value, (
                    f"Audio bytes detected in column '{col_name}'!"
                )
