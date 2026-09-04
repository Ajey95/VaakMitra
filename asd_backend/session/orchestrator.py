"""
Session Orchestrator — M3.1

Coordinates the complete child attempt lifecycle:
  start_session → submit_attempt → cancel_attempt → end_session

The orchestrator calls Member 1 and Member 2 services through typed
interfaces (injected at construction time) so they can be mocked in tests.

Privacy rules enforced here
----------------------------
- Audio is held only as bytes in memory during processing.
- Audio is never passed to the database layer.
- After scoring completes (success, failure, timeout, or cancellation),
  the audio bytes reference is released.
- No intermediate (embeddings, MFCC, phoneme probabilities) is persisted.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import uuid
from typing import Optional

import structlog

from asd_backend.adaptive.engine import AdaptiveEngine
from asd_backend.adaptive.policy import TherapistPolicy
from asd_backend.adaptive.schemas import (
    ScoringResult,
    SessionState,
    SyllableScoreInput,
    PhonemeScoreInput,
)
from asd_backend.db.database import get_session_factory
from asd_backend.db.repositories import (
    AttemptRepository,
    AuditRepository,
    ConsentRepository,
    ExercisePlanRepository,
    PhonemeScoreRepository,
    SessionRepository,
    SyllableScoreRepository,
    SyncQueueRepository,
)
from asd_backend.config import settings
from asd_backend.session.schemas import (
    AttemptResult,
    CancelAttemptRequest,
    SessionEndResponse,
    SessionStartRequest,
    SessionStartResponse,
)
from asd_backend.sync.allow_list import build_sync_payload, SyncPolicyViolation

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Member 1 and Member 2 stub interfaces
# (Replace with real implementations once members deliver their modules)
# ---------------------------------------------------------------------------

class AudioCaptureResult:
    """Result returned by Member 1's audio capture + VAD + validation pipeline."""
    def __init__(
        self,
        attempt_id: str,
        capture_status: str,
        expected_word: str,
        expected_phonemes: list[str],
        phoneme_alignment: list[dict],
        alignment_confidence: Optional[float],
    ):
        self.attempt_id = attempt_id
        self.capture_status = capture_status
        self.expected_word = expected_word
        self.expected_phonemes = expected_phonemes
        self.phoneme_alignment = phoneme_alignment
        self.alignment_confidence = alignment_confidence


class Member1ServiceInterface:
    """
    Interface for Member 1's audio + alignment pipeline.
    Replaced by real implementation in production.
    """
    async def process(
        self,
        audio_bytes: bytes,
        target_word: str,
        exercise_id: str,
    ) -> AudioCaptureResult:
        raise NotImplementedError


class Member2ServiceInterface:
    """
    Interface for Member 2's acoustic model + GOP scoring pipeline.
    Replaced by real implementation in production.
    """
    async def score(
        self,
        audio_bytes: bytes,
        phoneme_alignment: list[dict],
        expected_phonemes: list[str],
        attempt_id: str,
    ) -> ScoringResult:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Stub implementations (used during Sprint 1 / integration testing)
# ---------------------------------------------------------------------------

class StubMember1Service(Member1ServiceInterface):
    """Returns deterministic dummy alignment for Sprint 1 integration."""

    dictionary_version = "ta-dict-1.0.0"

    async def process(
        self,
        audio_bytes: bytes,
        target_word: str,
        exercise_id: str,
    ) -> AudioCaptureResult:
        await asyncio.sleep(0)  # yield event loop
        attempt_id = f"ATT-{uuid.uuid4().hex[:8].upper()}"
        return AudioCaptureResult(
            attempt_id=attempt_id,
            capture_status="valid",
            expected_word=target_word,
            expected_phonemes=["a", "m", "m", "a:"],
            phoneme_alignment=[
                {"phoneme": "a",  "start_ms": 40,  "end_ms": 160, "confidence": 0.91},
                {"phoneme": "m",  "start_ms": 160, "end_ms": 300, "confidence": 0.87},
                {"phoneme": "m",  "start_ms": 300, "end_ms": 420, "confidence": 0.84},
                {"phoneme": "a:", "start_ms": 420, "end_ms": 760, "confidence": 0.79},
            ],
            alignment_confidence=0.85,
        )


class StubMember2Service(Member2ServiceInterface):
    """Returns deterministic dummy GOP scores for Sprint 1 integration."""

    model_version = "ta-phoneme-ctc-stub-1.0.0"

    async def score(
        self,
        audio_bytes: bytes,
        phoneme_alignment: list[dict],
        expected_phonemes: list[str],
        attempt_id: str,
    ) -> ScoringResult:
        await asyncio.sleep(0)
        return ScoringResult(
            attempt_id=attempt_id,
            model_version="ta-phoneme-ctc-stub-1.0.0",
            phoneme_scores=[
                PhonemeScoreInput(phoneme="a",  gop=0.90, confidence=0.92, status="pass"),
                PhonemeScoreInput(phoneme="m",  gop=0.82, confidence=0.88, status="pass"),
                PhonemeScoreInput(phoneme="m",  gop=0.71, confidence=0.81, status="coach"),
                PhonemeScoreInput(phoneme="a:", gop=0.48, confidence=0.77, status="retry"),
            ],
            syllable_scores=[
                SyllableScoreInput(syllable="அம்", score=0.86, status="pass"),
                SyllableScoreInput(syllable="மா",  score=0.56, status="coach"),
            ],
            overall_confidence=0.84,
        )


# ---------------------------------------------------------------------------
# Session Orchestrator
# ---------------------------------------------------------------------------

# Version constants — in production load from manifests / config
_DICT_VERSION = settings.dictionary_version


class SessionOrchestrator:
    """
    Async stateful session coordinator.

    One instance is shared across the FastAPI app (singleton).
    Session state is tracked in an in-memory dict keyed by session_id;
    the source-of-truth lives in the encrypted DB.
    """

    def __init__(
        self,
        member1: Optional[Member1ServiceInterface] = None,
        member2: Optional[Member2ServiceInterface] = None,
        policy: Optional[TherapistPolicy] = None,
    ) -> None:
        self._m1 = member1 or StubMember1Service()
        self._m2 = member2 or StubMember2Service()
        self._policy = policy or TherapistPolicy.default()
        self._engine = AdaptiveEngine()
        # In-memory session state: session_id → SessionState
        self._states: dict[str, SessionState] = {}
        self._exercise_catalogs: dict[str, dict[str, str]] = {}
        # In-flight attempt cancellation events
        self._cancel_events: dict[str, asyncio.Event] = {}

    @property
    def member1(self) -> Member1ServiceInterface:
        return self._m1

    @property
    def member2(self) -> Member2ServiceInterface:
        return self._m2

    @property
    def model_version(self) -> str:
        return getattr(self._m2, "model_version", settings.model_version)

    @property
    def dictionary_version(self) -> str:
        return getattr(self._m1, "dictionary_version", settings.dictionary_version)

    # ── start_session ─────────────────────────────────────────────────────────

    async def start_session(
        self, request: SessionStartRequest
    ) -> SessionStartResponse:
        log.info("session.start", pseudonym_id=request.pseudonym_id, plan_id=request.plan_id)

        async with get_session_factory()() as db:
            # Load exercise plan
            plan_repo = ExercisePlanRepository(db)
            exercises = await plan_repo.get_exercises(request.plan_id)
            if not exercises:
                raise ValueError(f"Exercise plan {request.plan_id!r} not found or empty")

            first_ex = exercises[0]

            # Create DB session record
            sess_repo = SessionRepository(db)
            db_session = await sess_repo.create(
                pseudonym_id=request.pseudonym_id,
                plan_id=request.plan_id,
            )

            # Audit
            audit = AuditRepository(db)
            await audit.log(
                event_type="session_start",
                pseudonym_id=request.pseudonym_id,
                session_id=db_session.session_id,
                detail={"plan_id": request.plan_id, "first_exercise": first_ex.get("id")},
            )

            await db.commit()

        # Initialise in-memory state
        session_id = db_session.session_id
        self._states[session_id] = SessionState(
            session_id=session_id,
            exercise_id=first_ex["id"],
            target_word=first_ex.get("target_word", ""),
            attempt_count=0,
            consecutive_retries=0,
            session_attempt_count=0,
            no_response_count=0,
            capture_status="",
            next_exercise_id=exercises[1]["id"] if len(exercises) > 1 else first_ex["id"],
        )
        self._exercise_catalogs[session_id] = {
            exercise["id"]: exercise.get("target_word", "") for exercise in exercises
        }

        log.info("session.started", session_id=session_id)
        return SessionStartResponse(
            session_id=session_id,
            plan_id=request.plan_id,
            status="active",
            first_exercise_id=first_ex["id"],
            first_target_word=first_ex.get("target_word", ""),
            policy_version=self._policy.policy_version,
            dict_version=_DICT_VERSION,
        )

    # ── submit_attempt ────────────────────────────────────────────────────────

    async def submit_attempt(
        self,
        session_id: str,
        exercise_id: str,
        target_word: str,
        audio_b64: str,
    ) -> AttemptResult:
        """
        Full attempt pipeline:
        audio → M1 capture+align → M2 score → adaptive decision → persist → respond

        Audio bytes are held only in this stack frame and are not persisted.
        """
        log.info("attempt.start", session_id=session_id, exercise_id=exercise_id)

        # Decode audio into memory
        try:
            audio_bytes: bytes = base64.b64decode(audio_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"Invalid audio_b64: {exc}") from exc
        if not audio_bytes:
            raise ValueError("Invalid audio_b64: decoded audio is empty")
        if len(audio_bytes) > settings.max_audio_bytes:
            raise ValueError(
                f"Audio exceeds maximum of {settings.max_audio_bytes} bytes"
            )

        state = self._states.get(session_id)
        if state is None:
            raise ValueError(f"Session {session_id!r} not found. Call start_session first.")
        assigned_word = self._exercise_catalogs.get(session_id, {}).get(exercise_id)
        if assigned_word is None or assigned_word != target_word:
            raise ValueError(
                "Submitted target_word does not match the assigned exercise plan"
            )

        # Register cancellation only after all request validation has succeeded.
        cancel_event = asyncio.Event()
        attempt_key = f"{session_id}::{exercise_id}::{uuid.uuid4().hex}"
        self._cancel_events[attempt_key] = cancel_event

        scoring: Optional[ScoringResult] = None
        m1_result: Optional[AudioCaptureResult] = None

        try:
            # ── Member 1: audio capture + VAD + forced alignment ──────────────
            m1_task = asyncio.create_task(
                self._m1.process(audio_bytes, target_word, exercise_id)
            )
            done, _ = await asyncio.wait(
                {m1_task}, timeout=settings.member1_timeout_s
            )
            if not done or cancel_event.is_set():
                m1_task.cancel()
                log.warning("attempt.m1_timeout_or_cancel", session_id=session_id)
                return await self._handle_invalid(
                    session_id, exercise_id, target_word,
                    capture_status="timeout", state=state,
                )

            m1_result = m1_task.result()
            attempt_id = m1_result.attempt_id

            # Update state capture status
            state.capture_status = m1_result.capture_status

            # ── Member 2: acoustic model + GOP scoring ────────────────────────
            if m1_result.capture_status == "valid":
                m2_task = asyncio.create_task(
                    self._m2.score(
                        audio_bytes,
                        m1_result.phoneme_alignment,
                        m1_result.expected_phonemes,
                        attempt_id,
                    )
                )
                done2, _ = await asyncio.wait(
                    {m2_task}, timeout=settings.member2_timeout_s
                )
                if not done2 or cancel_event.is_set():
                    m2_task.cancel()
                    log.warning("attempt.m2_timeout_or_cancel", session_id=session_id)
                    scoring = None
                else:
                    try:
                        scoring = m2_task.result()
                    except Exception as m2_exc:
                        log.warning("attempt.m2_error", error=str(m2_exc), session_id=session_id)
                        scoring = None

        finally:
            # Release audio bytes reference — help GC
            audio_bytes = b""
            self._cancel_events.pop(attempt_key, None)

        # ── Adaptive decision ─────────────────────────────────────────────────
        decision = self._engine.decide(scoring, state, self._policy)

        # ── Update in-memory session state ────────────────────────────────────
        self._update_state(state, decision, scoring)

        # ── Persist to DB (structured metrics only, no audio) ─────────────────
        persisted = False
        sync_eligible = False
        final_attempt_id = decision.attempt_id

        try:
            async with get_session_factory()() as db:
                attempt_repo = AttemptRepository(db)
                db_attempt = await attempt_repo.create(
                    session_id=session_id,
                    exercise_id=exercise_id,
                    target_word=target_word,
                    capture_status=state.capture_status,
                    model_version=scoring.model_version if scoring else "N/A",
                    dict_version=_DICT_VERSION,
                    policy_version=self._policy.policy_version,
                    decision=decision.result,
                    response_intent=decision.response_intent.value,
                    alignment_confidence=m1_result.alignment_confidence if m1_result else None,
                    overall_gop_confidence=scoring.overall_confidence if scoring else None,
                    sync_eligible=False,
                )
                final_attempt_id = db_attempt.attempt_id

                # Store phoneme / syllable scores
                if scoring:
                    ph_repo = PhonemeScoreRepository(db)
                    await ph_repo.bulk_create(
                        final_attempt_id,
                        [s.model_dump() for s in scoring.phoneme_scores],
                    )
                    syl_repo = SyllableScoreRepository(db)
                    await syl_repo.bulk_create(
                        final_attempt_id,
                        [s.model_dump() for s in scoring.syllable_scores],
                    )

                # Enqueue metric sync if eligible
                session_record = await SessionRepository(db).get(session_id)
                has_sync_consent = bool(
                    session_record
                    and await ConsentRepository(db).has_active_consent(
                        session_record.pseudonym_id, "metric_sync"
                    )
                )
                if decision.result == "pass" and scoring and has_sync_consent:
                    sync_eligible = True
                    db_attempt.sync_eligible = True
                    try:
                        sync_repo = SyncQueueRepository(db)
                        payload = build_sync_payload(
                            pseudonym_id=session_record.pseudonym_id,
                            session_id=session_id,
                            attempt_id=final_attempt_id,
                            exercise_id=exercise_id,
                            syllable_scores=[s.model_dump() for s in scoring.syllable_scores],
                            overall_pass=(decision.result == "pass"),
                            model_version=scoring.model_version,
                            dict_version=_DICT_VERSION,
                            policy_version=self._policy.policy_version,
                        )
                        await sync_repo.enqueue(
                            idempotency_key=f"attempt-{final_attempt_id}",
                            payload=payload,
                        )
                    except SyncPolicyViolation as exc:
                        log.error("sync.policy_violation", error=str(exc))

                # Audit
                audit = AuditRepository(db)
                await audit.log(
                    event_type="attempt",
                    session_id=session_id,
                    detail={
                        "attempt_id": final_attempt_id,
                        "exercise_id": exercise_id,
                        "decision": decision.result,
                        "capture_status": state.capture_status,
                    },
                )
                await db.commit()
                persisted = True

        except Exception as exc:
            log.error("attempt.persist_error", error=str(exc), session_id=session_id)

        # ── Build Unity response ──────────────────────────────────────────────
        prompt_audio_id = self._policy.prompt_audio_map.get(
            decision.response_intent.value,
            "ta_generic_v1.wav",
        )

        return AttemptResult(
            session_id=session_id,
            attempt_id=final_attempt_id,
            result=decision.result,
            weak_unit=decision.weak_unit,
            response_intent=decision.response_intent.value,
            prompt_audio_id=prompt_audio_id,
            avatar_state=decision.avatar_state.value,
            next_exercise_id=decision.next_exercise_id,
            attempts_remaining=decision.attempts_remaining,
            persisted=persisted,
            sync_eligible=sync_eligible,
            model_version=scoring.model_version if scoring else self.model_version,
            dict_version=(
                getattr(m1_result, "dictionary_version", self.dictionary_version)
                if m1_result else self.dictionary_version
            ),
            policy_version=self._policy.policy_version,
        )

    # ── cancel_attempt ────────────────────────────────────────────────────────

    async def cancel_attempt(self, request: CancelAttemptRequest) -> None:
        """Signal cancellation to any in-flight attempt for this session."""
        log.info("attempt.cancel", session_id=request.session_id)
        for key, event in list(self._cancel_events.items()):
            if key.startswith(request.session_id):
                event.set()

    # ── end_session ───────────────────────────────────────────────────────────

    async def end_session(self, session_id: str) -> SessionEndResponse:
        log.info("session.end", session_id=session_id)
        state = self._states.pop(session_id, None)
        self._exercise_catalogs.pop(session_id, None)

        sync_queued = False

        async with get_session_factory()() as db:
            sess_repo = SessionRepository(db)
            attempt_repo = AttemptRepository(db)
            total_attempts, total_exercises = await attempt_repo.session_totals(session_id)
            if await sess_repo.get(session_id) is None:
                raise ValueError(f"Session {session_id!r} not found")
            await sess_repo.end(
                session_id=session_id,
                status="completed",
                total_attempts=total_attempts,
                total_exercises=total_exercises,
            )
            audit = AuditRepository(db)
            await audit.log(
                event_type="session_end",
                session_id=session_id,
                detail={"total_attempts": total_attempts},
            )
            # Check if there are pending sync items
            sq = SyncQueueRepository(db)
            pending = await sq.pending()
            sync_queued = len(pending) > 0
            await db.commit()

        return SessionEndResponse(
            session_id=session_id,
            status="completed",
            total_attempts=total_attempts,
            total_exercises=total_exercises,
            sync_queued=sync_queued,
        )

    # ── private helpers ───────────────────────────────────────────────────────

    async def _handle_invalid(
        self,
        session_id: str,
        exercise_id: str,
        target_word: str,
        capture_status: str,
        state: SessionState,
    ) -> AttemptResult:
        """Build a neutral retry result for an invalid/timed-out capture."""
        state.capture_status = capture_status
        decision = self._engine.decide(None, state, self._policy)
        prompt_audio_id = self._policy.prompt_audio_map.get(
            decision.response_intent.value, "ta_generic_v1.wav"
        )
        return AttemptResult(
            session_id=session_id,
            attempt_id=f"ATT-INVALID-{uuid.uuid4().hex[:6].upper()}",
            result=decision.result,
            weak_unit=None,
            response_intent=decision.response_intent.value,
            prompt_audio_id=prompt_audio_id,
            avatar_state=decision.avatar_state.value,
            next_exercise_id=decision.next_exercise_id,
            attempts_remaining=decision.attempts_remaining,
            persisted=False,
            sync_eligible=False,
            model_version=self.model_version,
            dict_version=self.dictionary_version,
            policy_version=self._policy.policy_version,
        )

    def _update_state(
        self,
        state: SessionState,
        decision,
        scoring: Optional[ScoringResult],
    ) -> None:
        """Update in-memory session counters after a decision."""
        state.session_attempt_count += 1
        state.attempt_count += 1

        if state.capture_status in ("silence", "timeout"):
            state.no_response_count += 1
        else:
            state.no_response_count = 0

        if decision.result in ("retry", "low_confidence_retry"):
            state.consecutive_retries += 1
        else:
            state.consecutive_retries = 0

        # Advance to next exercise on pass or break
        if decision.result in ("pass", "break"):
            state.exercise_id = decision.next_exercise_id
            state.attempt_count = 0
            state.consecutive_retries = 0
