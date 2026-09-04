"""
Session orchestrator tests — M3.5

Tests the full attempt pipeline via the session orchestrator
using stub Member 1 and Member 2 services.
"""

from __future__ import annotations

import asyncio
import base64
import uuid

import pytest

from asd_backend.adaptive.policy import TherapistPolicy
from asd_backend.db.repositories import (
    ChildProfileRepository,
    ExercisePlanRepository,
    SessionRepository,
    AttemptRepository,
)
from asd_backend.session.orchestrator import (
    SessionOrchestrator,
    StubMember1Service,
    StubMember2Service,
)
from asd_backend.session.schemas import (
    CancelAttemptRequest,
    SessionStartRequest,
)
from tests.conftest import _use_test_engine

SAMPLE_EXERCISES = [
    {
        "id": "TA_AMMA_01",
        "target_word": "அம்மா",
        "target_phonemes": ["a", "m", "m", "a:"],
        "syllables": ["அம்", "மா"],
        "difficulty": "easy",
    },
    {
        "id": "TA_APPA_01",
        "target_word": "அப்பா",
        "target_phonemes": ["a", "p", "p", "a:"],
        "syllables": ["அப்", "பா"],
        "difficulty": "easy",
    },
]


@pytest.fixture
def orchestrator():
    return SessionOrchestrator(
        member1=StubMember1Service(),
        member2=StubMember2Service(),
        policy=TherapistPolicy.default(),
    )


@pytest.fixture
def silent_audio_b64():
    pcm_silence = bytes(16000 * 2)
    return base64.b64encode(pcm_silence).decode()


# ---------------------------------------------------------------------------
# Helpers — seed DB via test_db fixture
# ---------------------------------------------------------------------------

async def _seed_plan(test_db) -> tuple[str, str]:
    """Create child + plan, return (pseudonym_id, plan_id)."""
    child_repo = ChildProfileRepository(test_db)
    await child_repo.create("child-orch-test", consent_version="1.0")
    plan_repo = ExercisePlanRepository(test_db)
    plan = await plan_repo.create(
        therapist_ref="test-therapist",
        policy_version="0.0.1-dev",
        plan_version="1.0.0",
        exercises=SAMPLE_EXERCISES,
    )
    await test_db.commit()
    return "child-orch-test", plan.plan_id


# ---------------------------------------------------------------------------
# Session lifecycle tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_session_returns_first_exercise(orchestrator, test_db, test_engine):
    """start_session must return the first exercise from the plan."""
    await _use_test_engine(test_engine)

    pseudonym_id, plan_id = await _seed_plan(test_db)
    request = SessionStartRequest(pseudonym_id=pseudonym_id, plan_id=plan_id)
    response = await orchestrator.start_session(request)

    assert response.session_id is not None
    assert response.first_exercise_id == "TA_AMMA_01"
    assert response.first_target_word == "அம்மா"
    assert response.status == "active"


@pytest.mark.asyncio
async def test_submit_attempt_returns_result(orchestrator, test_db, test_engine, silent_audio_b64):
    """submit_attempt must return a structured AttemptResult."""
    await _use_test_engine(test_engine)

    pseudonym_id, plan_id = await _seed_plan(test_db)
    start_resp = await orchestrator.start_session(
        SessionStartRequest(pseudonym_id=pseudonym_id, plan_id=plan_id)
    )
    result = await orchestrator.submit_attempt(
        session_id=start_resp.session_id,
        exercise_id="TA_AMMA_01",
        target_word="அம்மா",
        audio_b64=silent_audio_b64,
    )

    assert result.session_id == start_resp.session_id
    assert result.attempt_id is not None
    assert result.result in {"pass", "targeted_coaching", "retry", "break", "no_response"}
    assert result.response_intent is not None
    assert result.avatar_state is not None
    assert result.prompt_audio_id is not None


@pytest.mark.asyncio
async def test_attempt_persisted_to_db(orchestrator, test_db, test_engine, silent_audio_b64):
    """Structured metrics from an attempt must be saved to the DB."""
    await _use_test_engine(test_engine)

    pseudonym_id, plan_id = await _seed_plan(test_db)
    start_resp = await orchestrator.start_session(
        SessionStartRequest(pseudonym_id=pseudonym_id, plan_id=plan_id)
    )
    result = await orchestrator.submit_attempt(
        session_id=start_resp.session_id,
        exercise_id="TA_AMMA_01",
        target_word="அம்மா",
        audio_b64=silent_audio_b64,
    )

    assert result.persisted is True

    # Verify attempt is in DB
    attempt_repo = AttemptRepository(test_db)
    attempts = await attempt_repo.list_for_session(start_resp.session_id)
    assert len(attempts) == 1
    assert attempts[0].target_word == "அம்மா"
    assert attempts[0].model_version is not None
    assert attempts[0].dict_version is not None
    assert attempts[0].policy_version is not None


@pytest.mark.asyncio
async def test_invalid_session_id_raises(orchestrator, silent_audio_b64):
    """submit_attempt with unknown session_id must raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await orchestrator.submit_attempt(
            session_id="NONEXISTENT-SESSION",
            exercise_id="TA_AMMA_01",
            target_word="அம்மா",
            audio_b64=silent_audio_b64,
        )


@pytest.mark.asyncio
async def test_cancel_attempt_does_not_raise(orchestrator):
    """cancel_attempt must not raise even if no in-flight attempt exists."""
    await orchestrator.cancel_attempt(
        CancelAttemptRequest(session_id="SES-NOOP", reason="user_cancelled")
    )


@pytest.mark.asyncio
async def test_end_session_completes(orchestrator, test_db, test_engine):
    """end_session must mark session as completed and return summary."""
    await _use_test_engine(test_engine)

    pseudonym_id, plan_id = await _seed_plan(test_db)
    start_resp = await orchestrator.start_session(
        SessionStartRequest(pseudonym_id=pseudonym_id, plan_id=plan_id)
    )
    end_resp = await orchestrator.end_session(start_resp.session_id)

    assert end_resp.status == "completed"
    assert end_resp.session_id == start_resp.session_id
