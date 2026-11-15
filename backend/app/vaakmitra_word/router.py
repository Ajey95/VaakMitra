"""Canonical word API and scoring readiness (SSOT Section 13)."""

from __future__ import annotations

import io
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import DuplicateKeyError

from ..config import settings
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import oid
from ..utils.rate_limit import RateLimiter
from .assessment import AssessmentContext
from .contracts import AssessmentResult, ReasonCode
from .curriculum import build_lesson_catalog, lesson_target
from .inference_runner import inference_runner
from .registry import ServiceRegistry, build_runtime
from .report_access import report_share_allowed, utc
from .session_limits import SessionLimits
from .session_state import WordSessionStore
from .upload_limit import MemoryOnlyWordRoute
from .vocabulary import VocabularyRegistry

router = APIRouter(tags=["word-assessment"], route_class=MemoryOnlyWordRoute)

ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav", "audio/wave", "application/octet-stream",
}

WORD_CATALOG = {
    "TA_00001": "அ", "TA_00002": "ஆ", "TA_00003": "ல",
    "TA_00004": "ட", "TA_00021": "அம்மா", "TA_00022": "அப்பா",
}
VOCABULARY_PATH = Path(__file__).resolve().parents[2] / "data" / "vocabulary" / "ta-v1-intended.json"
VOCABULARY_REGISTRY = VocabularyRegistry.from_json(VOCABULARY_PATH)
LESSON_CATALOG = build_lesson_catalog(VOCABULARY_REGISTRY)


class AssessmentService(Protocol):
    def assess(self, audio_bytes: bytes, context: AssessmentContext) -> AssessmentResult: ...


class UnavailableAssessmentService:
    def __init__(self, reason: ReasonCode = ReasonCode.MODEL_UNAVAILABLE) -> None:
        self.reason = reason

    def assess(self, _audio_bytes: bytes, context: AssessmentContext) -> AssessmentResult:
        return AssessmentResult.unscorable(
            self.reason,
            session_id=context.session_id,
            attempt_id=context.attempt_id,
            word_id=context.word_id,
            target_word=context.target_word,
        )


class WordSessionStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str = Field(min_length=1, max_length=64)


class WordSessionResume(BaseModel):
    model_config = ConfigDict(extra="forbid")
    next_word_id: str | None = Field(default=None, max_length=64)


class ReportShareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guardian_evidence_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    valid_until: datetime


class ReportShareVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guardian_relationship_verified: bool


_service: AssessmentService = UnavailableAssessmentService()

_bundle_config = settings.VAAKMITRA_BUNDLE_CONFIG.strip()
_registry, configured_service = build_runtime(Path(_bundle_config) if _bundle_config else Path())
if configured_service is not None:
    _service = configured_service
else:
    readiness_reasons = _registry.scoring_readiness().reasons
    if any("calibration" in reason for reason in readiness_reasons):
        _service = UnavailableAssessmentService(ReasonCode.CALIBRATION_UNAVAILABLE)
    elif any(reason.startswith("model_") for reason in readiness_reasons):
        _service = UnavailableAssessmentService(ReasonCode.MODEL_UNAVAILABLE)
    else:
        _service = UnavailableAssessmentService(ReasonCode.ARTIFACT_MISMATCH)


def get_readiness_registry():
    return _registry


def get_assessment_service() -> AssessmentService:
    return _service


def get_word_session_store(db=Depends(get_database)) -> WordSessionStore:
    return WordSessionStore(db, VOCABULARY_REGISTRY)


def canonical_word(word_id: str, target_word: str) -> str:
    registered = next(
        (entry for entry in VOCABULARY_REGISTRY.entries if entry.word_id == word_id),
        None,
    )
    if registered is not None:
        if registered.canonical_tamil != target_word.strip():
            raise ValueError("word_id and target_word do not match the server-owned exercise catalog")
        return registered.canonical_tamil
    expected = WORD_CATALOG.get(word_id)
    if expected is None or expected != target_word.strip():
        raise ValueError("word_id and target_word do not match the server-owned exercise catalog")
    return expected


def canonical_for_lesson(lesson_id: int, legacy_target: str) -> tuple[str, str]:
    return lesson_target(LESSON_CATALOG, lesson_id, legacy_target)


def _next_registry_word(word_id: str) -> str:
    word_ids = [entry.word_id for entry in VOCABULARY_REGISTRY.entries]
    try:
        position = word_ids.index(word_id)
    except ValueError:
        return "TA_00022"
    return word_ids[min(position + 1, len(word_ids) - 1)]


async def bounded_audio(upload: UploadFile) -> bytes:
    if upload.content_type and upload.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="unsupported_audio_type")
    maximum = int(settings.MAX_UPLOAD_BYTES)
    data = await upload.read(maximum + 1)
    if not data:
        raise HTTPException(status_code=400, detail="empty_audio")
    if len(data) > maximum:
        raise HTTPException(status_code=413, detail="audio_too_large")
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise HTTPException(status_code=415, detail="unsupported_audio_type")
    try:
        with wave.open(io.BytesIO(data), "rb") as source:
            channels, width, rate, frames = (
                source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getnframes(),
            )
            expected = channels * width * frames
            if (source.getcomptype() != "NONE" or channels < 1 or width not in (1, 2, 4)
                    or rate <= 0 or expected <= 0 or expected > len(data)
                    or len(source.readframes(frames)) != expected):
                raise ValueError("unsupported PCM WAV layout")
    except (wave.Error, EOFError, ValueError) as exc:
        raise HTTPException(status_code=415, detail="unsupported_audio_type") from exc
    return data


@router.get("/api/v1/word-plans/assigned")
async def assigned_word_plans(current_user: dict = Depends(get_current_user),
                              db=Depends(get_database),
                              session_store: WordSessionStore = Depends(get_word_session_store)):
    """SES-001/UX-007: discover only this child's current plans and recover its session."""
    if current_user.get('role') != 'user':
        raise HTTPException(403, detail='child_plan_view_required')
    child_id = str(current_user['_id'])
    child = await db.users.find_one({'_id': oid(child_id), 'role': 'user'})
    if not child or not child.get('therapist_id'):
        return {'plans': [], 'open_session': None}
    candidates = await db.treatment_plans.find({'child_id': child_id, 'status': 'active',
        'therapist_id': child['therapist_id']}).to_list(length=100)
    registered = {entry.word_id for entry in VOCABULARY_REGISTRY.entries
                  if entry.kind == 'word' and entry.state in ('intended', 'active')}
    plans = []
    for plan in candidates:
        words = plan.get('word_ids') or []
        if (not words or len(words) > 25 or len(set(words)) != len(words)
                or not set(words).issubset(registered)
                or plan.get('vocabulary_version') != VOCABULARY_REGISTRY.version
                or 'session_limits' not in plan):
            continue
        try:
            limits = SessionLimits.model_validate(plan['session_limits'])
        except ValueError:
            continue
        plans.append({'plan_id': str(plan['_id']), 'word_ids': words,
                      'vocabulary_version': plan['vocabulary_version'],
                      'session_limits': limits.model_dump(), 'status': 'active'})
    open_session = None
    current = await db.word_sessions.find_one({'owner_id': child_id, 'status': {'$in': ['active', 'paused']}})
    if current:
        try:
            open_session = await session_store.snapshot(current['_id'], current_user)
        except HTTPException as exc:
            if exc.status_code not in (403, 404, 409):
                raise
    return {'plans': plans, 'open_session': open_session}


@router.post("/api/v1/word-sessions", status_code=201)
async def start_word_session(
    request: WordSessionStart,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """Section 13.1: a client can start only a currently assigned, versioned plan."""
    plan = await db.treatment_plans.find_one({"_id": oid(request.plan_id)})
    if not plan or plan.get("status") != "active":
        raise HTTPException(status_code=404, detail="active_word_plan_not_found")
    owner_id = plan.get("child_id")
    child = await db.users.find_one({"_id": oid(owner_id)}) if owner_id else None
    if not child or child.get("role") != "user":
        raise HTTPException(status_code=404, detail="assigned_child_not_found")
    actor_id = str(current_user["_id"])
    role = current_user.get("role")
    if child.get("therapist_id") != plan.get("therapist_id"):
        raise HTTPException(status_code=403, detail="word_plan_assignment_changed")
    if role != "admin" and not (
        role == "user" and actor_id == owner_id or
        role == "therapist" and actor_id == plan.get("therapist_id")
        and child.get("therapist_id") == actor_id
    ):
        raise HTTPException(status_code=403, detail="word_plan_access_denied")
    word_ids = plan.get("word_ids") or []
    if "session_limits" not in plan:
        raise HTTPException(status_code=409, detail="word_plan_limits_required")
    try:
        limits = SessionLimits.model_validate(plan["session_limits"])
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="word_plan_limits_invalid") from exc
    vocabulary_version = plan.get("vocabulary_version")
    registered = {entry.word_id: entry for entry in VOCABULARY_REGISTRY.entries
                  if entry.kind == "word" and entry.state in ("intended", "active")}
    if (not word_ids or len(word_ids) > 25 or len(set(word_ids)) != len(word_ids)
            or vocabulary_version != VOCABULARY_REGISTRY.version
            or any(word_id not in registered for word_id in word_ids)):
        raise HTTPException(status_code=409, detail="word_plan_not_ready")
    plan_id = str(plan["_id"])
    if await db.word_sessions.find_one({"owner_id": owner_id, "status": {"$in": ["active", "paused"]}}):
        raise HTTPException(status_code=409, detail="word_plan_session_already_open")
    recent = await db.word_sessions.find_one({"owner_id": owner_id, "restart_after": {"$gt": datetime.now(timezone.utc)}})
    if recent:
        raise HTTPException(status_code=409, detail="word_session_break_required")
    session_id = f"SES-{uuid4().hex}"
    try:
        await db.word_sessions.insert_one({
            "_id": session_id, "owner_id": owner_id, "plan_id": plan_id,
            "therapist_id": plan.get("therapist_id"), "word_ids": word_ids,
            "vocabulary_version": vocabulary_version, "current_index": 0,
            "attempt_count": 0, "status": "active", "inflight_attempt_id": None,
            "session_limits": limits.model_dump(), "total_attempts": 0,
            "completed_attempt_ids": [], "attempts": [], "session_events": [],
            "created_at": datetime.now(timezone.utc),
        })
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="word_plan_session_already_open") from exc
    first = registered[word_ids[0]]
    return {"session_id": session_id, "word_id": first.word_id,
            "target_word": first.canonical_tamil, "exercise_version": vocabulary_version,
            "attempt_count": 0, "status": "active"}


@router.post("/api/v1/word-assessments", response_model=AssessmentResult)
async def create_word_assessment(
    audio: UploadFile = File(...),
    session_id: str = Form(..., min_length=1, max_length=128),
    attempt_id: str = Form(..., min_length=1, max_length=128),
    word_id: str = Form(..., min_length=1, max_length=64),
    target_word: str = Form(..., min_length=1, max_length=128),
    exercise_version: str = Form(..., min_length=1, max_length=64),
    current_user: dict = Depends(get_current_user),
    service: AssessmentService = Depends(get_assessment_service),
    session_store: WordSessionStore = Depends(get_word_session_store),
):
    if inference_runner.busy:
        raise HTTPException(503, detail="model_busy", headers={"Retry-After": "2"})
    try:
        target = canonical_word(word_id, target_word)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if exercise_version not in ("ta-core-1.0.0", VOCABULARY_REGISTRY.version):
        raise HTTPException(status_code=422, detail="unsupported exercise_version")
    data = await bounded_audio(audio)
    claim = await session_store.claim(session_id, attempt_id, word_id, target, exercise_version, current_user)
    context = claim.assessment
    try:
        result = await inference_runner.run(service.assess, data, context,
            timeout=settings.VAAKMITRA_INFERENCE_TIMEOUT_SECONDS)
    except TimeoutError:
        result = AssessmentResult.unscorable(
            ReasonCode.MODEL_TIMEOUT,
            session_id=context.session_id,
            attempt_id=context.attempt_id,
            word_id=context.word_id,
            target_word=context.target_word,
        )
    except Exception:
        result = AssessmentResult.unscorable(
            ReasonCode.MODEL_INFERENCE_FAILED,
            session_id=context.session_id, attempt_id=context.attempt_id,
            word_id=context.word_id, target_word=context.target_word,
        )
    return await session_store.complete(claim, result)


@router.post("/api/v1/word-sessions/{session_id}/stop")
async def stop_word_session(session_id: str, current_user: dict = Depends(get_current_user),
                            session_store: WordSessionStore = Depends(get_word_session_store)):
    """Section 14.1: stop wins over any in-flight inference."""
    return await session_store.stop(session_id, current_user)


@router.get("/api/v1/word-sessions/{session_id}")
async def get_word_session(session_id: str, current_user: dict = Depends(get_current_user),
                           session_store: WordSessionStore = Depends(get_word_session_store)):
    """DEC-016: return only the next server-owned word and coarse session state."""
    return await session_store.snapshot(session_id, current_user)


@router.post("/api/v1/word-sessions/{session_id}/pause")
async def pause_word_session(session_id: str, current_user: dict = Depends(get_current_user),
                             session_store: WordSessionStore = Depends(get_word_session_store)):
    return await session_store.pause(session_id, current_user)


@router.post("/api/v1/word-sessions/{session_id}/resume")
async def resume_word_session(session_id: str, request: WordSessionResume,
                              current_user: dict = Depends(get_current_user),
                              session_store: WordSessionStore = Depends(get_word_session_store),
                              registry=Depends(get_readiness_registry)):
    if not registry.scoring_readiness().ready:
        raise HTTPException(503, detail="scoring_unavailable")
    return await session_store.resume(session_id, current_user, next_word_id=request.next_word_id)


@router.get("/api/v1/word-sessions/{session_id}/summary")
async def word_session_summary(session_id: str, current_user: dict = Depends(get_current_user),
                                session_store: WordSessionStore = Depends(get_word_session_store)):
    return await session_store.summary(session_id, current_user)


@router.get("/api/v1/word-session-reports")
async def list_word_session_reports(current_user: dict = Depends(get_current_user),
                                    db=Depends(get_database),
                                    session_store: WordSessionStore = Depends(get_word_session_store)):
    """RPT-001/007: only persisted, ended sessions become unsigned report views."""
    actor_id = str(current_user["_id"])
    role = current_user.get("role")
    if role == "user":
        query = {"owner_id": actor_id, "status": {"$in": ["ended", "complete", "expired"]}}
    elif role == "therapist":
        query = {"therapist_id": actor_id, "status": {"$in": ["ended", "complete", "expired"]}}
    else:
        raise HTTPException(403, detail="word_report_access_denied")
    candidates = await db.word_sessions.find(query).sort("created_at", -1).limit(20).to_list(length=20)
    reports = []
    for session in candidates:
        if role == "therapist" and not await report_share_allowed(db, session["owner_id"], actor_id):
            continue
        try:
            report = await session_store.summary(session["_id"], current_user)
        except HTTPException as exc:
            if exc.status_code in (403, 404, 409):
                continue
            raise
        reports.append({**report, "review_status": "not_signed"})
    return {"reports": reports}


@router.post("/api/v1/report-sharing", status_code=201,
             dependencies=[Depends(RateLimiter(30, 60))])
async def request_report_sharing(payload: ReportShareRequest,
                                 current_user: dict = Depends(get_current_user),
                                 db=Depends(get_database)):
    """RPT-004/007: a caregiver request is pending, never effective consent."""
    if current_user.get("role") != "user":
        raise HTTPException(403, detail="caregiver_account_required")
    child_id = str(current_user["_id"])
    child = await db.users.find_one({"_id": oid(child_id)})
    therapist_id = child.get("therapist_id") if child else None
    if not therapist_id:
        raise HTTPException(409, detail="assigned_therapist_required")
    now = datetime.now(timezone.utc)
    if (payload.valid_until.tzinfo is None or utc(payload.valid_until) <= now
            or utc(payload.valid_until) > now + timedelta(days=365)):
        raise HTTPException(422, detail="report_share_validity_invalid")
    grant_id = uuid4().hex
    await db.report_share_grants.insert_one({
        "_id": grant_id, "child_id": child_id, "therapist_id": therapist_id,
        "purpose": "word_session_report", "status": "pending",
        "submitted_by": child_id, "guardian_evidence_sha256": payload.guardian_evidence_sha256,
        "valid_until": payload.valid_until, "created_at": now,
    })
    await db.audit_logs.insert_one({"action": "report_share.requested", "actor_id": child_id,
                                    "target_id": grant_id, "created_at": now})
    return {"grant_id": grant_id, "status": "pending"}


@router.post("/api/v1/report-sharing/{grant_id}/verify",
             dependencies=[Depends(RateLimiter(30, 60))])
async def verify_report_sharing(grant_id: str, payload: ReportShareVerification,
                                current_user: dict = Depends(get_current_user),
                                db=Depends(get_database)):
    """RPT-004/007: only a different administrator can attest the guardian evidence."""
    if current_user.get("role") != "admin":
        raise HTTPException(403, detail="admin_required")
    grant = await db.report_share_grants.find_one({"_id": grant_id})
    if not grant or grant.get("status") != "pending":
        raise HTTPException(404, detail="pending_report_share_not_found")
    if str(current_user["_id"]) == grant.get("submitted_by") or not payload.guardian_relationship_verified:
        raise HTTPException(403, detail="independent_guardian_verification_required")
    child = await db.users.find_one({"_id": oid(grant["child_id"])})
    now = datetime.now(timezone.utc)
    if (not child or child.get("therapist_id") != grant.get("therapist_id")
            or not isinstance(grant.get("valid_until"), datetime)
            or utc(grant["valid_until"]) <= now):
        raise HTTPException(409, detail="report_share_assignment_or_validity_changed")
    result = await db.report_share_grants.update_one({"_id": grant_id, "status": "pending"},
        {"$set": {"status": "verified", "verified_at": now,
                  "verified_by": str(current_user["_id"]), "guardian_relationship_verified": True}})
    if result.modified_count != 1:
        raise HTTPException(409, detail="report_share_transition_conflict")
    await db.audit_logs.insert_one({"action": "report_share.verified",
        "actor_id": str(current_user["_id"]), "target_id": grant_id, "created_at": now})
    return {"grant_id": grant_id, "status": "verified"}


@router.post("/api/v1/report-sharing/{grant_id}/withdraw",
             dependencies=[Depends(RateLimiter(30, 60))])
async def withdraw_report_sharing(grant_id: str, current_user: dict = Depends(get_current_user),
                                  db=Depends(get_database)):
    """RPT-004/007: withdrawal immediately revokes future therapist reads."""
    if current_user.get("role") != "user":
        raise HTTPException(403, detail="caregiver_account_required")
    child_id = str(current_user["_id"])
    grant = await db.report_share_grants.find_one({"_id": grant_id, "child_id": child_id})
    if not grant or grant.get("status") not in ("pending", "verified"):
        raise HTTPException(404, detail="active_report_share_not_found")
    latest = await db.report_share_grants.find_one(
        {"child_id": child_id}, sort=[("created_at", -1), ("_id", -1)],
    )
    if not latest or latest.get("_id") != grant_id:
        raise HTTPException(409, detail="report_share_not_current")
    now = datetime.now(timezone.utc)
    result = await db.report_share_grants.update_one({"_id": grant_id, "child_id": child_id,
        "status": grant["status"]}, {"$set": {"status": "withdrawn", "withdrawn_at": now}})
    if result.modified_count != 1:
        raise HTTPException(409, detail="report_share_transition_conflict")
    await db.audit_logs.insert_one({"action": "report_share.withdrawn",
        "actor_id": child_id, "target_id": grant_id, "created_at": now})
    return {"grant_id": grant_id, "status": "withdrawn"}


@router.get("/api/v1/vocabulary")
async def list_vocabulary(_current_user: dict = Depends(get_current_user)):
    """Expose the versioned registry without implying unavailable scoring (DEC-016)."""
    return {
        "schema_version": VOCABULARY_REGISTRY.schema_version,
        "vocabulary_version": VOCABULARY_REGISTRY.version,
        "entries": [
            {
                "word_id": entry.word_id,
                "canonical_tamil": entry.canonical_tamil,
                "english_gloss": entry.english_gloss,
                "category": entry.category,
                "kind": entry.kind,
                "state": entry.state,
                "available_for_scoring": (
                    entry.state == "active"
                    and entry.scoreable
                    and entry.human_review.status == "approved"
                ),
            }
            for entry in VOCABULARY_REGISTRY.entries
        ],
    }


@router.get("/health/scoring")
async def scoring_health(registry: ServiceRegistry = Depends(get_readiness_registry)):
    readiness = registry.scoring_readiness()
    if not readiness.ready:
        raise HTTPException(status_code=503, detail=readiness.model_dump(mode="json"))
    return readiness
