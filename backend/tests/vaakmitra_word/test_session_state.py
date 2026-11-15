"""DEC-008 / Section 13.1 and 14.1: atomic word-session transitions."""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.vaakmitra_word.contracts import AssessmentResult, Decision, ReasonCode
from app.vaakmitra_word.router import VOCABULARY_REGISTRY
from app.vaakmitra_word.session_limits import SessionLimits
from app.vaakmitra_word.session_state import WordSessionStore

CHILD_ID = "0000000000000000000000c1"
THERAPIST_ID = "0000000000000000000000d1"
PLAN_ID = "0000000000000000000000e1"


class Documents:
    def __init__(self, docs):
        self.docs = docs

    async def find_one(self, query):
        return next((deepcopy(doc) for doc in self.docs
                     if all(doc.get(key) == value for key, value in query.items())), None)


class Sessions:
    def __init__(self):
        self.doc = {
            "_id": "SES-1", "owner_id": CHILD_ID, "therapist_id": THERAPIST_ID,
            "plan_id": PLAN_ID,
            "word_ids": ["TA_WORD_0001", "TA_WORD_0002"],
            "vocabulary_version": "ta-words-v1.1.0", "current_index": 0,
            "attempt_count": 0, "status": "active", "inflight_attempt_id": None,
            "completed_attempt_ids": [],
            "session_limits": SessionLimits().model_dump(), "total_attempts": 0,
            "attempts": [], "created_at": datetime.now(timezone.utc),
        }

    def matches(self, query):
        for key, expected in query.items():
            actual = self.doc.get(key)
            if isinstance(expected, dict) and "$ne" in expected:
                if expected["$ne"] in (actual or []):
                    return False
            elif isinstance(expected, dict) and "$in" in expected:
                if actual not in expected["$in"]:
                    return False
            elif actual != expected:
                return False
        return True

    async def find_one(self, query):
        return deepcopy(self.doc) if self.matches(query) else None

    async def find_one_and_update(self, query, update, **_kwargs):
        if not self.matches(query):
            return None
        old = deepcopy(self.doc)
        self.apply(update)
        return old

    async def update_one(self, query, update):
        if not self.matches(query):
            return SimpleNamespace(modified_count=0)
        self.apply(update)
        return SimpleNamespace(modified_count=1)

    def apply(self, update):
        self.doc.update(update.get("$set", {}))
        for key, value in update.get("$inc", {}).items():
            self.doc[key] = self.doc.get(key, 0) + value
        for key, value in update.get("$push", {}).items():
            self.doc.setdefault(key, []).append(value)
        for key, value in update.get("$addToSet", {}).items():
            if value not in self.doc.setdefault(key, []):
                self.doc[key].append(value)


def store():
    sessions = Sessions()
    db = SimpleNamespace(
        word_sessions=sessions,
        treatment_plans=Documents([{"_id": ObjectId(PLAN_ID), "status": "active",
                                    "child_id": CHILD_ID, "therapist_id": THERAPIST_ID,
                                    "word_ids": ["TA_WORD_0001", "TA_WORD_0002"],
                                    "session_limits": SessionLimits().model_dump(),
                                    "vocabulary_version": "ta-words-v1.1.0"}]),
        users=Documents([{"_id": ObjectId(CHILD_ID), "role": "user", "therapist_id": THERAPIST_ID}]),
    )
    return WordSessionStore(db, VOCABULARY_REGISTRY), sessions


def unscorable(attempt_id):
    return AssessmentResult.unscorable(ReasonCode.MODEL_UNAVAILABLE,
        session_id="SES-1", attempt_id=attempt_id, word_id="TA_WORD_0001", target_word="அம்மா")


def claim(repository, attempt_id="ATT-1", *, actor=CHILD_ID, word="TA_WORD_0001"):
    return repository.claim("SES-1", attempt_id, word, "அம்மா", "ta-words-v1.1.0",
                            {"_id": actor, "role": "user"})


def test_ses003_stop_still_works_for_legacy_missing_limits():
    repository, sessions = store()
    del sessions.doc['session_limits']
    result = asyncio.run(repository.stop('SES-1', {'_id': CHILD_ID, 'role': 'user'}))
    assert result['status'] == 'ended'
    assert sessions.doc['inflight_attempt_id'] is None


def test_ses005_owner_can_read_summary_after_plan_retirement():
    repository, sessions = store()
    repository.db.treatment_plans.docs[0]['status'] = 'inactive'
    sessions.doc['status'] = 'ended'
    summary = asyncio.run(repository.summary('SES-1', {'_id': CHILD_ID, 'role': 'user'}))
    assert summary['completed_attempts'] == 0


def test_rpt001_002_summary_has_denominated_word_trajectory_without_fabricated_accuracy():
    repository, sessions = store()
    sessions.doc['status'] = 'ended'
    sessions.doc['total_attempts'] = 5
    sessions.doc['attempts'] = [
        {'word_id': 'TA_WORD_0001', 'decision': 'RETRY', 'reason_code': 'CALIBRATED_WORD_MISMATCH', 'response_intent': 'ENCOURAGE_RETRY'},
        {'word_id': 'TA_WORD_0001', 'decision': 'PASS', 'reason_code': 'CALIBRATED_TARGET_MATCH', 'response_intent': 'CELEBRATE'},
        {'word_id': 'TA_WORD_0002', 'decision': 'UNSCORABLE', 'reason_code': 'INVALID_AUDIO', 'response_intent': 'NEUTRAL_RETRY'},
        {'word_id': 'TA_WORD_0002', 'decision': 'PASS', 'reason_code': 'CALIBRATED_TARGET_MATCH', 'response_intent': 'CELEBRATE'},
    ]
    summary = asyncio.run(repository.summary('SES-1', {'_id': CHILD_ID, 'role': 'user'}))
    assert summary['metrics'] == {
        'planned_words': 2, 'attempted_words': 2, 'scoreable_words': 2,
        'first_scoreable_pass_words': 1, 'eventual_pass_words': 2,
        'total_captures': 5, 'completed_attempts': 4, 'captures_without_completion': 1,
        'scoreable_attempts': 3, 'retry_attempts': 1, 'unscorable_attempts': 1,
        'voluntary_breaks': 0,
    }
    assert [row['word_id'] for row in summary['timeline']] == ['TA_WORD_0001'] * 2 + ['TA_WORD_0002'] * 2
    assert summary['timeline'][2]['reason_code'] == 'INVALID_AUDIO'
    assert summary['word_labels']['TA_WORD_0001'] == 'அம்மா'
    assert summary['word_labels']['TA_WORD_0002'] == 'அப்பா'
    assert 'accuracy' not in summary
    assert 'transcript' not in str(summary).lower()
    assert 'probability' not in str(summary).lower()


def test_section13_rejects_wrong_owner_or_unassigned_word():
    repository, sessions = store()
    with pytest.raises(HTTPException) as denied:
        asyncio.run(claim(repository, actor="other"))
    assert denied.value.status_code == 403
    with pytest.raises(HTTPException) as mismatched:
        asyncio.run(claim(repository, word="TA_WORD_0002"))
    assert mismatched.value.status_code == 422
    assert sessions.doc["inflight_attempt_id"] is None


def test_section13_stale_or_revoked_plan_cannot_claim_new_audio():
    repository, sessions = store()
    repository.db.users.docs[0]["therapist_id"] = "other-therapist"
    with pytest.raises(HTTPException) as reassigned:
        asyncio.run(claim(repository))
    assert reassigned.value.status_code in (403, 409)
    repository.db.users.docs[0]["therapist_id"] = THERAPIST_ID
    repository.db.treatment_plans.docs[0]["status"] = "inactive"
    with pytest.raises(HTTPException) as revoked:
        asyncio.run(claim(repository))
    assert revoked.value.status_code == 409
    assert sessions.doc["inflight_attempt_id"] is None


def test_section13_reassigned_therapist_cannot_read_stale_session_word():
    repository, _sessions = store()
    repository.db.users.docs[0]["therapist_id"] = "other-therapist"
    with pytest.raises(HTTPException) as denied:
        asyncio.run(repository.snapshot("SES-1", {"_id": THERAPIST_ID, "role": "therapist"}))
    assert denied.value.status_code in (403, 409)


def test_dec008_duplicate_attempt_has_no_second_transition_and_unscorable_does_not_advance():
    repository, sessions = store()
    context = asyncio.run(claim(repository))
    with pytest.raises(HTTPException) as duplicate:
        asyncio.run(claim(repository))
    assert duplicate.value.status_code == 409
    decision = asyncio.run(repository.complete(context, unscorable("ATT-1")))
    assert decision.decision is Decision.UNSCORABLE
    assert sessions.doc["current_index"] == 0
    assert sessions.doc["attempt_count"] == 0
    assert sessions.doc["completed_attempt_ids"] == ["ATT-1"]
    with pytest.raises(HTTPException) as replay:
        asyncio.run(claim(repository))
    assert replay.value.status_code == 409


@pytest.mark.parametrize("reason", [ReasonCode.MODEL_TIMEOUT, ReasonCode.MODEL_INFERENCE_FAILED])
def test_section14_inference_failures_pause_instead_of_reprompting(reason):
    repository, sessions = store()
    context = asyncio.run(claim(repository))
    failed = AssessmentResult.unscorable(reason, session_id="SES-1", attempt_id="ATT-1",
        word_id="TA_WORD_0001", target_word="அம்மா")
    asyncio.run(repository.complete(context, failed))
    assert sessions.doc["status"] == "paused"


def test_section14_retries_use_stored_attempt_count_and_approved_next_word():
    repository, sessions = store()
    first = asyncio.run(claim(repository))
    assert first.assessment.attempt_count == 0
    assert first.assessment.therapist_constraints.next_exercise_id == "TA_WORD_0002"
    retry = AssessmentResult(session_id="SES-1", attempt_id="ATT-1", word_id="TA_WORD_0001",
        target_word="அம்மா", decision=Decision.RETRY, reason_code=ReasonCode.CALIBRATED_WORD_MISMATCH,
        word_match_probability=0.1)
    asyncio.run(repository.complete(first, retry))
    second = asyncio.run(claim(repository, attempt_id="ATT-2"))
    assert second.assessment.attempt_count == 1
    assert sessions.doc["attempt_count"] == 1


def test_section14_invalid_capture_does_not_erase_prior_retry_count():
    repository, sessions = store()
    sessions.doc["attempt_count"] = 1
    context = asyncio.run(claim(repository))
    capture = AssessmentResult.unscorable(ReasonCode.INVALID_AUDIO,
        session_id="SES-1", attempt_id="ATT-1", word_id="TA_WORD_0001", target_word="அம்மா")
    asyncio.run(repository.complete(context, capture))
    assert sessions.doc["attempt_count"] == 1
    assert sessions.doc["current_index"] == 0


def test_section14_policy_break_at_max_retries_pauses_session():
    repository, sessions = store()
    sessions.doc["attempt_count"] = 2
    context = asyncio.run(claim(repository))
    retry = AssessmentResult(session_id="SES-1", attempt_id="ATT-1", word_id="TA_WORD_0001",
        target_word="அம்மா", decision=Decision.RETRY, reason_code=ReasonCode.CALIBRATED_WORD_MISMATCH,
        word_match_probability=0.1, response_intent="OFFER_BREAK", avatar_state="BREAK")
    asyncio.run(repository.complete(context, retry))
    assert sessions.doc["status"] == "paused"
    assert sessions.doc["current_index"] == 0


def test_section14_stop_prevents_late_pass_and_stores_no_score_or_audio():
    repository, sessions = store()
    context = asyncio.run(claim(repository))
    asyncio.run(repository.stop("SES-1", {"_id": CHILD_ID, "role": "user"}))
    late_pass = AssessmentResult(session_id="SES-1", attempt_id="ATT-1", word_id="TA_WORD_0001",
        target_word="அம்மா", decision=Decision.PASS, reason_code=ReasonCode.CALIBRATED_TARGET_MATCH,
        word_match_probability=0.9)
    decision = asyncio.run(repository.complete(context, late_pass))
    assert decision.decision is Decision.UNSCORABLE
    assert decision.reason_code is ReasonCode.CANCELLED
    assert sessions.doc["current_index"] == 0
    assert sessions.doc["status"] == "ended"
    assert set(sessions.doc) == {
        "_id", "owner_id", "therapist_id", "plan_id", "word_ids", "vocabulary_version", "current_index",
        "attempt_count", "status", "inflight_attempt_id", "inflight_claim_token", "completed_attempt_ids",
        "session_limits", "total_attempts", "attempts", "session_events", "created_at", "lease_expires_at", "ended_at", "restart_after",
    }


def test_section14_pass_advances_only_to_the_next_assigned_word():
    repository, sessions = store()
    context = asyncio.run(claim(repository))
    passed = AssessmentResult(session_id="SES-1", attempt_id="ATT-1", word_id="TA_WORD_0001",
        target_word="அம்மா", decision=Decision.PASS, reason_code=ReasonCode.CALIBRATED_TARGET_MATCH,
        word_match_probability=0.9, next_exercise_id="TA_WORD_0002")
    asyncio.run(repository.complete(context, passed))
    next_word = asyncio.run(repository.snapshot("SES-1", {"_id": CHILD_ID, "role": "user"}))
    assert next_word["word_id"] == "TA_WORD_0002"
    assert next_word["target_word"] == "அப்பா"
    assert sessions.doc["attempt_count"] == 0
    assert sessions.doc["status"] == "active"


def test_section13_plan_revocation_during_inference_cancels_late_pass():
    repository, sessions = store()
    context = asyncio.run(claim(repository))
    repository.db.treatment_plans.docs[0]["status"] = "inactive"
    late_pass = AssessmentResult(session_id="SES-1", attempt_id="ATT-1", word_id="TA_WORD_0001",
        target_word="அம்மா", decision=Decision.PASS, reason_code=ReasonCode.CALIBRATED_TARGET_MATCH,
        word_match_probability=0.9)
    result = asyncio.run(repository.complete(context, late_pass))
    assert result.decision is Decision.UNSCORABLE
    assert sessions.doc["current_index"] == 0


def test_ses003_pause_snapshot_claim_race_cannot_replay_or_commit_old_pass():
    repository, sessions = store()
    original = repository._require_current_plan
    captured = []
    interleaved = [False]
    async def interleave_claim_after_pause_snapshot(session):
        await original(session)
        if not interleaved[0]:
            interleaved[0] = True
            captured.append(await claim(repository, attempt_id='ATT-1'))
    repository._require_current_plan = interleave_claim_after_pause_snapshot
    actor = {'_id': CHILD_ID, 'role': 'user'}
    adult = {'_id': THERAPIST_ID, 'role': 'therapist'}
    asyncio.run(repository.pause('SES-1', actor))
    assert len(captured) == 1
    assert sessions.doc['inflight_attempt_id'] is None
    asyncio.run(repository.resume('SES-1', adult))
    with pytest.raises(HTTPException) as replay:
        asyncio.run(claim(repository, attempt_id='ATT-1'))
    assert replay.value.status_code == 409
    old_pass = AssessmentResult(session_id='SES-1', attempt_id='ATT-1', word_id='TA_WORD_0001',
        target_word='அம்மா', decision=Decision.PASS, reason_code=ReasonCode.CALIBRATED_TARGET_MATCH,
        word_match_probability=0.9)
    result = asyncio.run(repository.complete(captured[0], old_pass))
    assert result.decision is Decision.UNSCORABLE
    assert result.reason_code is ReasonCode.CANCELLED
    assert sessions.doc['current_index'] == 0
    assert sessions.doc['attempts'] == []


def test_ses004_dec020_owner_resumes_voluntary_break_only_after_plan_interval():
    repository, sessions = store()
    current = [sessions.doc['created_at']]
    repository.clock = lambda: current[0]
    actor = {'_id': CHILD_ID, 'role': 'user'}
    sessions.doc['attempt_count'] = 1
    sessions.doc['total_attempts'] = 2
    asyncio.run(repository.pause('SES-1', actor))
    assert sessions.doc['pause_reason'] == 'user_pause'
    with pytest.raises(HTTPException) as early:
        asyncio.run(repository.resume('SES-1', actor))
    assert early.value.detail == 'completed_break_required'
    current[0] += timedelta(seconds=30)
    resumed = asyncio.run(repository.resume('SES-1', actor))
    assert resumed['status'] == 'active'
    assert resumed['word_id'] == 'TA_WORD_0001'
    assert sessions.doc['attempt_count'] == 1
    assert sessions.doc['total_attempts'] == 2


def test_rpt001_ses007_break_and_end_events_are_recorded_once_for_report():
    repository, sessions = store()
    current = [sessions.doc['created_at']]
    repository.clock = lambda: current[0]
    actor = {'_id': CHILD_ID, 'role': 'user'}
    asyncio.run(repository.pause('SES-1', actor))
    current[0] += timedelta(seconds=30)
    asyncio.run(repository.resume('SES-1', actor))
    asyncio.run(repository.stop('SES-1', actor))
    asyncio.run(repository.stop('SES-1', actor))
    summary = asyncio.run(repository.summary('SES-1', actor))
    assert [event['type'] for event in summary['session_events']] == [
        'break_started', 'break_ended', 'session_ended',
    ]
    assert summary['metrics']['voluntary_breaks'] == 1
    assert summary['break_data_status'] == 'recorded'


def test_rpt001_malformed_event_times_remain_explicitly_unavailable():
    from app.vaakmitra_word.session_report import build_session_summary
    session = {
        '_id': 'SES-LEGACY', 'status': 'ended', 'word_ids': ['TA_WORD_0001'],
        'created_at': datetime.now(timezone.utc), 'total_attempts': 0,
        'session_events': [{'type': 'break_started', 'reason': 'user_pause', 'at': 'invalid'}],
    }
    report = build_session_summary(session)
    assert report['session_events'][0]['session_second'] is None


@pytest.mark.parametrize('pause_reason', ['retry_limit', 'capability', 'model_timeout'])
def test_ses004_dec020_owner_cannot_resume_safety_pause(pause_reason):
    repository, sessions = store()
    actor = {'_id': CHILD_ID, 'role': 'user'}
    sessions.doc.update(status='paused', pause_reason=pause_reason, paused_at=sessions.doc['created_at'])
    repository.clock = lambda: sessions.doc['created_at'] + timedelta(seconds=30)
    with pytest.raises(HTTPException) as denied:
        asyncio.run(repository.resume('SES-1', actor))
    assert denied.value.status_code == 403
    assert sessions.doc['status'] == 'paused'


def test_ses003_completion_requires_original_claim_generation():
    repository, sessions = store()
    first = asyncio.run(claim(repository, attempt_id='ATT-1'))
    sessions.doc['inflight_claim_token'] = 'another-generation'
    old_pass = AssessmentResult(session_id='SES-1', attempt_id='ATT-1', word_id='TA_WORD_0001',
        target_word='அம்மா', decision=Decision.PASS, reason_code=ReasonCode.CALIBRATED_TARGET_MATCH,
        word_match_probability=0.9)
    result = asyncio.run(repository.complete(first, old_pass))
    assert result.decision is Decision.UNSCORABLE
    assert result.reason_code is ReasonCode.CANCELLED
    assert sessions.doc['current_index'] == 0
    assert sessions.doc['attempts'] == []
