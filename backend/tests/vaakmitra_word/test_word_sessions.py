"""SSOT 13.1 / DEC-016: only server-owned plan words may enter a session."""

import io
import wave
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

from app.database import get_database
from app.utils.jwt_handler import get_current_user
from app.vaakmitra_word.contracts import AssessmentResult, ReasonCode
from app.vaakmitra_word.router import get_assessment_service, router
from app.vaakmitra_word.session_limits import SessionLimits

CHILD = ObjectId("0000000000000000000000c1")
OTHER = ObjectId("0000000000000000000000c2")
THERAPIST = ObjectId("0000000000000000000000d1")
PLAN = ObjectId("0000000000000000000000e1")


class Collection:
    def __init__(self, docs=()):
        self.docs = list(docs)

    async def find_one(self, query, sort=None):
        rows = [doc for doc in self.docs if self._matches(doc, query)]
        if sort:
            for field, direction in reversed(sort):
                rows.sort(key=lambda row: row.get(field) or '', reverse=direction < 0)
        return deepcopy(rows[0]) if rows else None

    def find(self, query):
        rows = [deepcopy(doc) for doc in self.docs if self._matches(doc, query)]
        class Cursor:
            def sort(self, field, direction):
                rows.sort(key=lambda row: row.get(field) or '', reverse=direction < 0)
                return self

            def limit(self, length):
                del rows[length:]
                return self

            async def to_list(self, length):
                return rows[:length]
        return Cursor()

    @staticmethod
    def _matches(doc, query):
        for key, expected in query.items():
            actual = doc.get(key)
            if isinstance(expected, dict) and "$ne" in expected:
                if expected["$ne"] in (actual if isinstance(actual, list) else [actual]):
                    return False
            elif isinstance(expected, dict) and "$in" in expected:
                if actual not in expected["$in"]:
                    return False
            elif isinstance(expected, dict) and "$gt" in expected:
                if actual is None or actual <= expected["$gt"]:
                    return False
            elif actual != expected:
                return False
        return True

    @staticmethod
    def _apply(doc, update):
        doc.update(update.get("$set", {}))
        for key, value in update.get("$inc", {}).items():
            doc[key] = doc.get(key, 0) + value
        for key, value in update.get("$push", {}).items():
            doc.setdefault(key, []).append(value)
        for key, value in update.get("$addToSet", {}).items():
            if value not in doc.setdefault(key, []):
                doc[key].append(value)

    async def find_one_and_update(self, query, update, **_kwargs):
        doc = next((item for item in self.docs if self._matches(item, query)), None)
        if doc is None:
            return None
        old = deepcopy(doc)
        self._apply(doc, update)
        return old

    async def update_one(self, query, update):
        doc = next((item for item in self.docs if self._matches(item, query)), None)
        if doc is None:
            return SimpleNamespace(modified_count=0)
        self._apply(doc, update)
        return SimpleNamespace(modified_count=1)

    async def insert_one(self, doc):
        if any(item.get("plan_id") == doc.get("plan_id") and item.get("status") in ("active", "paused")
               for item in self.docs):
            raise DuplicateKeyError("active_plan_session")
        self.docs.append(dict(doc))


class SessionDb:
    def __init__(self, *, words=None, version="ta-words-v1.1.0"):
        self.treatment_plans = Collection([{
            "_id": PLAN, "child_id": str(CHILD), "therapist_id": str(THERAPIST),
            "status": "active", "word_ids": words if words is not None else ["TA_WORD_0001", "TA_WORD_0002"],
            "vocabulary_version": version,
            "session_limits": SessionLimits().model_dump(),
        }])
        self.users = Collection([{"_id": CHILD, "role": "user", "therapist_id": str(THERAPIST)}])
        self.word_sessions = Collection()
        self.report_share_grants = Collection()
        self.audit_logs = Collection()


def client(db, actor):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_database] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: actor
    return TestClient(app)


def test_section13_session_uses_assigned_plan_word_and_pseudonymous_id():
    db = SessionDb()
    api = client(db, {"_id": CHILD, "role": "user"})
    response = api.post("/api/v1/word-sessions", json={"plan_id": str(PLAN)})
    assert response.status_code == 201
    assert response.json()["word_id"] == "TA_WORD_0001"
    assert response.json()["target_word"] == "அம்மா"
    assert response.json()["exercise_version"] == "ta-words-v1.1.0"
    assert response.json()["session_id"].startswith("SES-")
    assert set(db.word_sessions.docs[0]) == {
        "_id", "owner_id", "plan_id", "therapist_id", "word_ids", "vocabulary_version",
        "current_index", "attempt_count", "status", "inflight_attempt_id", "created_at",
        "session_limits", "total_attempts", "completed_attempt_ids", "attempts", "session_events",
    }
    snapshot = api.get(f"/api/v1/word-sessions/{response.json()['session_id']}")
    assert snapshot.status_code == 200
    assert snapshot.json()["word_id"] == "TA_WORD_0001"


def test_ses001_assigned_plan_discovery_is_scoped_and_recovers_open_session():
    db = SessionDb()
    db.treatment_plans.docs.append({**db.treatment_plans.docs[0], '_id': ObjectId(), 'child_id': str(OTHER)})
    api = client(db, {'_id': CHILD, 'role': 'user'})
    response = api.get('/api/v1/word-plans/assigned')
    assert response.status_code == 200
    assert [p['plan_id'] for p in response.json()['plans']] == [str(PLAN)]
    assert response.json()['open_session'] is None
    session = api.post('/api/v1/word-sessions', json={'plan_id': str(PLAN)}).json()
    recovered = api.get('/api/v1/word-plans/assigned').json()['open_session']
    assert recovered['session_id'] == session['session_id']
    assert recovered['target_word'] == 'அம்மா'


def test_rpt003_007_report_list_is_real_and_current_therapist_scoped():
    db = SessionDb()
    owner = client(db, {'_id': CHILD, 'role': 'user'})
    session = owner.post('/api/v1/word-sessions', json={'plan_id': str(PLAN)}).json()
    assert owner.post(f"/api/v1/word-sessions/{session['session_id']}/stop").status_code == 200
    own_reports = owner.get('/api/v1/word-session-reports')
    assert own_reports.status_code == 200
    assert len(own_reports.json()['reports']) == 1
    assert own_reports.json()['reports'][0]['metrics']['planned_words'] == 2
    assert own_reports.json()['reports'][0]['metrics']['completed_attempts'] == 0
    assert own_reports.json()['reports'][0]['review_status'] == 'not_signed'
    therapist = client(db, {'_id': THERAPIST, 'role': 'therapist'})
    assert therapist.get('/api/v1/word-session-reports').json()['reports'] == []
    db.report_share_grants.docs.append({
        'child_id': str(CHILD), 'therapist_id': str(THERAPIST),
        'purpose': 'word_session_report', 'status': 'verified',
        'guardian_relationship_verified': True, 'submitted_by': str(CHILD),
        'verified_by': str(OTHER), 'verified_at': datetime.now(timezone.utc),
        'created_at': datetime.now(timezone.utc),
        'guardian_evidence_sha256': 'a' * 64,
        'valid_until': datetime.now(timezone.utc) + timedelta(days=1),
    })
    assert len(therapist.get('/api/v1/word-session-reports').json()['reports']) == 1
    db.report_share_grants.docs[0]['status'] = 'withdrawn'
    assert therapist.get('/api/v1/word-session-reports').json()['reports'] == []
    db.report_share_grants.docs[0]['status'] = 'verified'
    db.users.docs[0]['therapist_id'] = str(OTHER)
    assert therapist.get('/api/v1/word-session-reports').json()['reports'] == []
    assert client(db, {'_id': OTHER, 'role': 'user'}).get('/api/v1/word-session-reports').json()['reports'] == []


def test_rpt004_007_caregiver_request_needs_independent_verification_and_can_withdraw():
    db = SessionDb()
    owner = client(db, {'_id': CHILD, 'role': 'user'})
    therapist = client(db, {'_id': THERAPIST, 'role': 'therapist'})
    admin = client(db, {'_id': OTHER, 'role': 'admin'})
    session = owner.post('/api/v1/word-sessions', json={'plan_id': str(PLAN)}).json()
    owner.post(f"/api/v1/word-sessions/{session['session_id']}/stop")
    requested = owner.post('/api/v1/report-sharing', json={
        'guardian_evidence_sha256': 'a' * 64,
        'valid_until': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    })
    assert requested.status_code == 201
    grant_id = requested.json()['grant_id']
    assert requested.json()['status'] == 'pending'
    assert therapist.get('/api/v1/word-session-reports').json()['reports'] == []
    assert therapist.get(f"/api/v1/word-sessions/{session['session_id']}/summary").status_code == 403
    assert admin.get(f"/api/v1/word-sessions/{session['session_id']}/summary").status_code == 403
    assert owner.post(f'/api/v1/report-sharing/{grant_id}/verify', json={
        'guardian_relationship_verified': True,
    }).status_code == 403
    verified = admin.post(f'/api/v1/report-sharing/{grant_id}/verify', json={
        'guardian_relationship_verified': True,
    })
    assert verified.status_code == 200
    assert len(therapist.get('/api/v1/word-session-reports').json()['reports']) == 1
    assert therapist.get(f"/api/v1/word-sessions/{session['session_id']}/summary").status_code == 200
    assert owner.post(f'/api/v1/report-sharing/{grant_id}/withdraw').status_code == 200
    assert therapist.get('/api/v1/word-session-reports').json()['reports'] == []
    assert therapist.get(f"/api/v1/word-sessions/{session['session_id']}/summary").status_code == 403
    assert [row['action'] for row in db.audit_logs.docs] == [
        'report_share.requested', 'report_share.verified', 'report_share.withdrawn',
    ]


def test_rpt007_newer_pending_grant_revokes_older_verified_even_after_many_requests():
    db = SessionDb()
    owner = client(db, {'_id': CHILD, 'role': 'user'})
    therapist = client(db, {'_id': THERAPIST, 'role': 'therapist'})
    session = owner.post('/api/v1/word-sessions', json={'plan_id': str(PLAN)}).json()
    owner.post(f"/api/v1/word-sessions/{session['session_id']}/stop")
    old = datetime.now(timezone.utc) - timedelta(days=2)
    db.report_share_grants.docs.append({
        '_id': 'old', 'child_id': str(CHILD), 'therapist_id': str(THERAPIST),
        'purpose': 'word_session_report', 'status': 'verified',
        'guardian_relationship_verified': True, 'submitted_by': str(CHILD),
        'verified_by': str(OTHER), 'verified_at': old,
        'created_at': old, 'guardian_evidence_sha256': 'a' * 64,
        'valid_until': datetime.now(timezone.utc) + timedelta(days=1),
    })
    assert len(therapist.get('/api/v1/word-session-reports').json()['reports']) == 1
    for i in range(100):
        db.report_share_grants.docs.append({
            **db.report_share_grants.docs[0], '_id': f'verified-{i}',
            'created_at': old + timedelta(minutes=i + 1),
        })
    db.report_share_grants.docs.append({
        '_id': 'new-pending', 'child_id': str(CHILD), 'therapist_id': str(THERAPIST),
        'status': 'pending', 'created_at': datetime.now(timezone.utc),
    })
    assert therapist.get('/api/v1/word-session-reports').json()['reports'] == []


def test_rpt001_report_list_picks_latest_even_after_one_hundred_sessions():
    db = SessionDb()
    owner = client(db, {'_id': CHILD, 'role': 'user'})
    original = owner.post('/api/v1/word-sessions', json={'plan_id': str(PLAN)}).json()
    owner.post(f"/api/v1/word-sessions/{original['session_id']}/stop")
    old = db.word_sessions.docs[0]
    for index in range(101):
        db.word_sessions.docs.append({
            **old, '_id': f'OLD-{index}',
            'created_at': old['created_at'] - timedelta(days=index + 1),
        })
    db.word_sessions.docs.append({
        **old, '_id': 'NEWEST', 'created_at': old['created_at'] + timedelta(seconds=1),
    })
    reports = owner.get('/api/v1/word-session-reports').json()['reports']
    assert len(reports) == 20
    assert reports[0]['session_id'] == 'NEWEST'


def test_rpt007_withdrawing_stale_grant_cannot_mislead_caregiver_about_active_share():
    db = SessionDb()
    owner = client(db, {'_id': CHILD, 'role': 'user'})
    first = owner.post('/api/v1/report-sharing', json={
        'guardian_evidence_sha256': 'a' * 64,
        'valid_until': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    }).json()['grant_id']
    second = owner.post('/api/v1/report-sharing', json={
        'guardian_evidence_sha256': 'b' * 64,
        'valid_until': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    }).json()['grant_id']
    stale = owner.post(f'/api/v1/report-sharing/{first}/withdraw')
    assert stale.status_code == 409
    assert stale.json()['detail'] == 'report_share_not_current'
    assert owner.post(f'/api/v1/report-sharing/{second}/withdraw').status_code == 200


def test_ses001_plan_discovery_rejects_stale_and_invalid_plans():
    db = SessionDb()
    api = client(db, {'_id': CHILD, 'role': 'user'})
    del db.treatment_plans.docs[0]['session_limits']
    assert api.get('/api/v1/word-plans/assigned').json()['plans'] == []
    db.treatment_plans.docs[0]['session_limits'] = SessionLimits().model_dump()
    db.users.docs[0]['therapist_id'] = str(OTHER)
    assert api.get('/api/v1/word-plans/assigned').json()['plans'] == []
    assert client(db, {'_id': THERAPIST, 'role': 'therapist'}).get('/api/v1/word-plans/assigned').status_code == 403


def test_section13_other_user_cannot_start_child_plan():
    db = SessionDb()
    response = client(db, {"_id": OTHER, "role": "user"}).post("/api/v1/word-sessions", json={"plan_id": str(PLAN)})
    assert response.status_code == 403
    assert db.word_sessions.docs == []


def test_section13_only_currently_assigned_therapist_can_start_plan():
    db = SessionDb()
    db.users.docs[0]["therapist_id"] = str(OTHER)
    response = client(db, {"_id": THERAPIST, "role": "therapist"}).post("/api/v1/word-sessions", json={"plan_id": str(PLAN)})
    assert response.status_code == 403
    assert db.word_sessions.docs == []


def test_section13_reassigned_child_cannot_start_stale_therapist_plan():
    db = SessionDb()
    db.users.docs[0]["therapist_id"] = str(OTHER)
    response = client(db, {"_id": CHILD, "role": "user"}).post("/api/v1/word-sessions", json={"plan_id": str(PLAN)})
    assert response.status_code == 403
    assert db.word_sessions.docs == []


def test_dec016_legacy_plan_without_word_assignment_fails_closed():
    db = SessionDb(words=[])
    response = client(db, {"_id": CHILD, "role": "user"}).post("/api/v1/word-sessions", json={"plan_id": str(PLAN)})
    assert response.status_code == 409
    assert db.word_sessions.docs == []


def test_section13_real_route_claims_owned_attempt_and_rejects_replay():
    db = SessionDb()
    api = client(db, {"_id": CHILD, "role": "user"})
    observed = []

    class UnavailableService:
        def assess(self, _audio, context):
            observed.append(context)
            return AssessmentResult.unscorable(ReasonCode.MODEL_UNAVAILABLE,
                session_id=context.session_id, attempt_id=context.attempt_id,
                word_id=context.word_id, target_word=context.target_word)

    api.app.dependency_overrides[get_assessment_service] = lambda: UnavailableService()
    started = api.post("/api/v1/word-sessions", json={"plan_id": str(PLAN)}).json()
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\x00" * 16000)
    fields = {"session_id": started["session_id"], "attempt_id": "ATT-1",
              "word_id": started["word_id"], "target_word": started["target_word"],
              "exercise_version": started["exercise_version"]}
    first = api.post("/api/v1/word-assessments", data=fields,
                     files={"audio": ("adult.wav", buffer.getvalue(), "audio/wav")})
    assert first.status_code == 200
    assert first.json()["decision"] == "UNSCORABLE"
    assert observed[0].attempt_count == 0
    assert db.word_sessions.docs[0]["current_index"] == 0
    duplicate = api.post("/api/v1/word-assessments", data=fields,
                         files={"audio": ("adult.wav", buffer.getvalue(), "audio/wav")})
    assert duplicate.status_code == 409
    assert len(observed) == 1


def test_section14_cannot_restart_an_active_or_paused_plan_to_reset_retries():
    db = SessionDb()
    api = client(db, {"_id": CHILD, "role": "user"})
    first = api.post("/api/v1/word-sessions", json={"plan_id": str(PLAN)})
    assert first.status_code == 201
    second = api.post("/api/v1/word-sessions", json={"plan_id": str(PLAN)})
    assert second.status_code == 409
    db.word_sessions.docs[0]["status"] = "paused"
    paused = api.post("/api/v1/word-sessions", json={"plan_id": str(PLAN)})
    assert paused.status_code == 409
    assert len(db.word_sessions.docs) == 1


def test_section14_duplicate_session_insert_race_returns_conflict():
    db = SessionDb()
    async def conflict(_doc):
        raise DuplicateKeyError("active_plan_session")
    db.word_sessions.insert_one = conflict
    response = client(db, {"_id": CHILD, "role": "user"}).post(
        "/api/v1/word-sessions", json={"plan_id": str(PLAN)})
    assert response.status_code == 409
