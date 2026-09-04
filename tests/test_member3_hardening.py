"""Member 3 safety and lifecycle behavior absent from the skeleton."""

import base64

import pytest
import pytest_asyncio

from asd_backend.adaptive.policy import TherapistPolicy
from asd_backend.adaptive.schemas import (
    PhonemeScoreInput,
    ScoringResult,
    SyllableScoreInput,
)
from asd_backend.db.repositories import (
    AttemptRepository,
    ChildProfileRepository,
    ExercisePlanRepository,
)
from asd_backend.session.orchestrator import SessionOrchestrator
from asd_backend.session.schemas import SessionStartRequest
from tests.conftest import SAMPLE_EXERCISES, _use_test_engine


@pytest_asyncio.fixture
async def hardened_orchestrator(test_db, test_engine):
    await _use_test_engine(test_engine)
    await ChildProfileRepository(test_db).create(
        "child-hardening-test", consent_version="1.0"
    )
    plan = await ExercisePlanRepository(test_db).create(
        therapist_ref="therapist",
        policy_version="0.0.1-dev",
        plan_version="1.0",
        exercises=SAMPLE_EXERCISES,
    )
    await test_db.commit()
    return SessionOrchestrator(policy=TherapistPolicy.default()), plan.plan_id


@pytest.mark.asyncio
async def test_submit_attempt_rejects_non_base64(hardened_orchestrator):
    orchestrator, plan_id = hardened_orchestrator
    start = await orchestrator.start_session(SessionStartRequest(
        pseudonym_id="child-hardening-test", plan_id=plan_id
    ))
    with pytest.raises(ValueError, match="Invalid audio_b64"):
        await orchestrator.submit_attempt(start.session_id, "TA_AMMA_01", "அம்மா", "%%%%")


@pytest.mark.asyncio
async def test_end_session_counts_attempts_and_distinct_exercises(
    hardened_orchestrator, test_db, silent_audio_b64
):
    orchestrator, plan_id = hardened_orchestrator
    start = await orchestrator.start_session(SessionStartRequest(
        pseudonym_id="child-hardening-test", plan_id=plan_id
    ))
    await orchestrator.submit_attempt(
        start.session_id, "TA_AMMA_01", "அம்மா", silent_audio_b64
    )
    await orchestrator.submit_attempt(
        start.session_id, "TA_APPA_01", "அப்பா", silent_audio_b64
    )
    result = await orchestrator.end_session(start.session_id)
    assert result.total_attempts == 2
    assert result.total_exercises == 2


@pytest.mark.asyncio
async def test_pass_is_not_sync_eligible_without_metric_sync_consent(
    hardened_orchestrator, test_db, silent_audio_b64
):
    orchestrator, plan_id = hardened_orchestrator
    class PassingScorer:
        async def score(self, audio_bytes, phoneme_alignment, expected_phonemes, attempt_id):
            return ScoringResult(
                attempt_id=attempt_id,
                model_version="ta-ctc-test-1",
                phoneme_scores=[
                    PhonemeScoreInput(phoneme="a", gop=0.95, confidence=0.95, status="pass")
                ],
                syllable_scores=[
                    SyllableScoreInput(syllable="அம்", score=0.95, status="pass")
                ],
                overall_confidence=0.95,
            )
    orchestrator._m2 = PassingScorer()
    start = await orchestrator.start_session(SessionStartRequest(
        pseudonym_id="child-hardening-test", plan_id=plan_id
    ))
    result = await orchestrator.submit_attempt(
        start.session_id, "TA_AMMA_01", "அம்மா", silent_audio_b64
    )
    assert result.sync_eligible is False
    attempts = await AttemptRepository(test_db).list_for_session(start.session_id)
    assert attempts[0].sync_eligible is False


@pytest.mark.asyncio
async def test_submit_attempt_rejects_audio_over_configured_limit(
    hardened_orchestrator
):
    orchestrator, plan_id = hardened_orchestrator
    start = await orchestrator.start_session(SessionStartRequest(
        pseudonym_id="child-hardening-test", plan_id=plan_id
    ))
    oversized = base64.b64encode(bytes(320_001)).decode()
    with pytest.raises(ValueError, match="maximum"):
        await orchestrator.submit_attempt(start.session_id, "TA_AMMA_01", "அம்மா", oversized)


@pytest.mark.asyncio
async def test_attempt_rejects_target_word_not_assigned_by_plan(
    hardened_orchestrator, silent_audio_b64
):
    orchestrator, plan_id = hardened_orchestrator
    start = await orchestrator.start_session(SessionStartRequest(
        pseudonym_id="child-hardening-test", plan_id=plan_id
    ))
    with pytest.raises(ValueError, match="does not match the assigned exercise"):
        await orchestrator.submit_attempt(
            start.session_id, "TA_AMMA_01", "தவறு", silent_audio_b64
        )
    assert orchestrator._cancel_events == {}


@pytest.mark.asyncio
async def test_attempt_response_has_independently_traceable_versions(
    hardened_orchestrator, silent_audio_b64
):
    orchestrator, plan_id = hardened_orchestrator
    start = await orchestrator.start_session(SessionStartRequest(
        pseudonym_id="child-hardening-test", plan_id=plan_id
    ))
    result = await orchestrator.submit_attempt(
        start.session_id,
        "TA_AMMA_01",
        SAMPLE_EXERCISES[0]["target_word"],
        silent_audio_b64,
    )
    assert result.model_version == "ta-phoneme-ctc-stub-1.0.0"
    assert result.dict_version == "ta-dict-1.0.0"
    assert result.policy_version == "0.0.1-dev"
