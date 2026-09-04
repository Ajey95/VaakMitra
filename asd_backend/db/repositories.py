"""
Typed async repository layer for all database entities.

Each repository encapsulates CRUD operations for one ORM model.
No raw SQL escapes this layer — all queries go through SQLAlchemy core/ORM.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import distinct, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from asd_backend.db.models import (
    Attempt,
    AuditEvent,
    ChildProfile,
    ConsentRecord,
    ExercisePlan,
    ModelVersionLog,
    PhonemeScore,
    Session,
    SyllableScore,
    SyncQueue,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# ChildProfileRepository
# ---------------------------------------------------------------------------

class ChildProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, pseudonym_id: str, consent_version: str) -> ChildProfile:
        profile = ChildProfile(
            pseudonym_id=pseudonym_id,
            consent_version=consent_version,
        )
        self._s.add(profile)
        await self._s.flush()
        return profile

    async def get(self, pseudonym_id: str) -> Optional[ChildProfile]:
        result = await self._s.execute(
            select(ChildProfile).where(ChildProfile.pseudonym_id == pseudonym_id)
        )
        return result.scalar_one_or_none()

    async def exists(self, pseudonym_id: str) -> bool:
        return await self.get(pseudonym_id) is not None


# ---------------------------------------------------------------------------
# ExercisePlanRepository
# ---------------------------------------------------------------------------

class ExercisePlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(
        self,
        therapist_ref: str,
        policy_version: str,
        plan_version: str,
        exercises: list[dict],
    ) -> ExercisePlan:
        plan = ExercisePlan(
            therapist_ref=therapist_ref,
            policy_version=policy_version,
            plan_version=plan_version,
            exercises_json=json.dumps(exercises, ensure_ascii=False),
        )
        self._s.add(plan)
        await self._s.flush()
        return plan

    async def get(self, plan_id: str) -> Optional[ExercisePlan]:
        result = await self._s.execute(
            select(ExercisePlan).where(ExercisePlan.plan_id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_exercises(self, plan_id: str) -> list[dict]:
        plan = await self.get(plan_id)
        if plan is None:
            return []
        return json.loads(plan.exercises_json)


# ---------------------------------------------------------------------------
# SessionRepository
# ---------------------------------------------------------------------------

class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, pseudonym_id: str, plan_id: str) -> Session:
        sess = Session(pseudonym_id=pseudonym_id, plan_id=plan_id, status="active")
        self._s.add(sess)
        await self._s.flush()
        return sess

    async def get(self, session_id: str) -> Optional[Session]:
        result = await self._s.execute(
            select(Session).where(Session.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def end(
        self,
        session_id: str,
        status: str = "completed",
        total_attempts: int = 0,
        total_exercises: int = 0,
    ) -> None:
        await self._s.execute(
            update(Session)
            .where(Session.session_id == session_id)
            .values(
                status=status,
                ended_at=_now(),
                total_attempts=total_attempts,
                total_exercises=total_exercises,
            )
        )

    async def cancel(self, session_id: str) -> None:
        await self.end(session_id, status="cancelled")

    async def list_active(self) -> Sequence[Session]:
        result = await self._s.execute(
            select(Session).where(Session.status == "active")
        )
        return result.scalars().all()


# ---------------------------------------------------------------------------
# AttemptRepository
# ---------------------------------------------------------------------------

class AttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(
        self,
        session_id: str,
        exercise_id: str,
        target_word: str,
        capture_status: str,
        model_version: str,
        dict_version: str,
        policy_version: str,
        decision: str,
        response_intent: str,
        alignment_confidence: Optional[float],
        overall_gop_confidence: Optional[float],
        sync_eligible: bool,
    ) -> Attempt:
        attempt = Attempt(
            session_id=session_id,
            exercise_id=exercise_id,
            target_word=target_word,
            capture_status=capture_status,
            model_version=model_version,
            dict_version=dict_version,
            policy_version=policy_version,
            decision=decision,
            response_intent=response_intent,
            alignment_confidence=alignment_confidence,
            overall_gop_confidence=overall_gop_confidence,
            sync_eligible=sync_eligible,
        )
        self._s.add(attempt)
        await self._s.flush()
        return attempt

    async def get(self, attempt_id: str) -> Optional[Attempt]:
        result = await self._s.execute(
            select(Attempt).where(Attempt.attempt_id == attempt_id)
        )
        return result.scalar_one_or_none()

    async def list_for_session(self, session_id: str) -> Sequence[Attempt]:
        result = await self._s.execute(
            select(Attempt).where(Attempt.session_id == session_id)
        )
        return result.scalars().all()

    async def session_totals(self, session_id: str) -> tuple[int, int]:
        """Return persisted attempt count and distinct attempted exercises."""
        result = await self._s.execute(
            select(
                func.count(Attempt.attempt_id),
                func.count(distinct(Attempt.exercise_id)),
            ).where(Attempt.session_id == session_id)
        )
        attempts, exercises = result.one()
        return int(attempts or 0), int(exercises or 0)

    async def count_retries_for_exercise(
        self, session_id: str, exercise_id: str
    ) -> int:
        result = await self._s.execute(
            select(Attempt).where(
                Attempt.session_id == session_id,
                Attempt.exercise_id == exercise_id,
                Attempt.capture_status == "valid",
            )
        )
        return len(result.scalars().all())


# ---------------------------------------------------------------------------
# PhonemeScoreRepository
# ---------------------------------------------------------------------------

class PhonemeScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def bulk_create(
        self,
        attempt_id: str,
        scores: list[dict],
    ) -> list[PhonemeScore]:
        objects = [
            PhonemeScore(
                attempt_id=attempt_id,
                phoneme=s["phoneme"],
                gop=s["gop"],
                confidence=s["confidence"],
                status=s["status"],
                position=i,
            )
            for i, s in enumerate(scores)
        ]
        self._s.add_all(objects)
        await self._s.flush()
        return objects


# ---------------------------------------------------------------------------
# SyllableScoreRepository
# ---------------------------------------------------------------------------

class SyllableScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def bulk_create(
        self,
        attempt_id: str,
        scores: list[dict],
    ) -> list[SyllableScore]:
        objects = [
            SyllableScore(
                attempt_id=attempt_id,
                syllable=s["syllable"],
                score=s["score"],
                status=s["status"],
                position=i,
            )
            for i, s in enumerate(scores)
        ]
        self._s.add_all(objects)
        await self._s.flush()
        return objects


# ---------------------------------------------------------------------------
# ModelVersionLogRepository
# ---------------------------------------------------------------------------

class ModelVersionLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def log(self, component: str, version: str) -> ModelVersionLog:
        entry = ModelVersionLog(component=component, version=version)
        self._s.add(entry)
        await self._s.flush()
        return entry

    async def latest(self, component: str) -> Optional[ModelVersionLog]:
        result = await self._s.execute(
            select(ModelVersionLog)
            .where(ModelVersionLog.component == component)
            .order_by(ModelVersionLog.loaded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# ConsentRepository
# ---------------------------------------------------------------------------

class ConsentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def grant(
        self,
        pseudonym_id: str,
        consent_type: str,
        version: str,
        granted_at: Optional[datetime] = None,
    ) -> ConsentRecord:
        record = ConsentRecord(
            pseudonym_id=pseudonym_id,
            consent_type=consent_type,
            version=version,
            granted_at=granted_at or _now(),
        )
        self._s.add(record)
        await self._s.flush()
        return record

    async def revoke(self, pseudonym_id: str, consent_type: str) -> None:
        result = await self._s.execute(
            select(ConsentRecord).where(
                ConsentRecord.pseudonym_id == pseudonym_id,
                ConsentRecord.consent_type == consent_type,
                ConsentRecord.revoked_at.is_(None),
            )
        )
        for record in result.scalars().all():
            record.revoked_at = _now()

    async def has_active_consent(self, pseudonym_id: str, consent_type: str) -> bool:
        result = await self._s.execute(
            select(ConsentRecord).where(
                ConsentRecord.pseudonym_id == pseudonym_id,
                ConsentRecord.consent_type == consent_type,
                ConsentRecord.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# AuditRepository
# ---------------------------------------------------------------------------

class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def log(
        self,
        event_type: str,
        pseudonym_id: Optional[str] = None,
        session_id: Optional[str] = None,
        detail: Optional[dict] = None,
    ) -> AuditEvent:
        ev = AuditEvent(
            event_type=event_type,
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            detail_json=json.dumps(detail) if detail else None,
        )
        self._s.add(ev)
        await self._s.flush()
        return ev

    async def has_sync_idempotency_key(self, idempotency_key: str) -> bool:
        """Check the append-only audit trail for an already ingested packet."""
        result = await self._s.execute(
            select(AuditEvent.detail_json).where(
                AuditEvent.event_type == "sync_received"
            )
        )
        for raw_detail in result.scalars():
            if not raw_detail:
                continue
            try:
                if json.loads(raw_detail).get("idempotency_key") == idempotency_key:
                    return True
            except (json.JSONDecodeError, AttributeError):
                continue
        return False


# ---------------------------------------------------------------------------
# SyncQueueRepository
# ---------------------------------------------------------------------------

class SyncQueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def enqueue(self, idempotency_key: str, payload: dict) -> SyncQueue:
        entry = SyncQueue(
            idempotency_key=idempotency_key,
            payload_json=json.dumps(payload, ensure_ascii=False),
            status="pending",
        )
        self._s.add(entry)
        await self._s.flush()
        return entry

    async def pending(self) -> Sequence[SyncQueue]:
        result = await self._s.execute(
            select(SyncQueue)
            .where(SyncQueue.status == "pending")
            .order_by(SyncQueue.created_at)
        )
        return result.scalars().all()

    async def mark_sent(self, entry_id: str) -> None:
        await self._s.execute(
            update(SyncQueue)
            .where(SyncQueue.entry_id == entry_id)
            .values(status="sent", last_attempt_at=_now())
        )

    async def mark_failed(self, entry_id: str, max_retries: int = 5) -> None:
        result = await self._s.execute(
            select(SyncQueue).where(SyncQueue.entry_id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if entry:
            entry.status = "failed"
            entry.retry_count += 1
            entry.last_attempt_at = _now()
            # Re-queue for retry if under limit
            if entry.retry_count < max_retries:
                entry.status = "pending"

    async def skip_malformed(self, entry_id: str) -> None:
        await self._s.execute(
            update(SyncQueue)
            .where(SyncQueue.entry_id == entry_id)
            .values(status="skipped", last_attempt_at=_now())
        )
