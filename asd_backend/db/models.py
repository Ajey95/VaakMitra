"""
SQLAlchemy ORM models for the ASD-Edge-ST local database.

Privacy invariants enforced here
---------------------------------
1. No column stores audio bytes, MFCC, embeddings, phoneme-probability
   sequences, spectrograms, transcripts, or any voice-derived representation.
2. Child references use pseudonymous UUIDs — no real names or device IDs.
3. An after-insert SQLAlchemy event raises PrivacyViolationError if any
   forbidden field name appears in an INSERT statement (defence-in-depth).

All timestamps are UTC.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid4() -> str:
    return str(uuid.uuid4())


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Privacy guard — forbidden column name fragments
# ---------------------------------------------------------------------------

_FORBIDDEN_COLUMN_FRAGMENTS = frozenset({
    "audio",
    "mfcc",
    "embedding",
    "spectrogram",
    "phoneme_prob",
    "probability",
    "transcript",
    "voiceprint",
    "waveform",
    "pcm",
})


class PrivacyViolationError(RuntimeError):
    """Raised when code attempts to persist a forbidden field to the DB."""


def _check_column_names(mapper, connection, target):  # noqa: ARG001
    """SQLAlchemy 'before_insert' event hook — rejects forbidden field names."""
    for col in mapper.columns:
        col_lower = col.key.lower()
        for fragment in _FORBIDDEN_COLUMN_FRAGMENTS:
            if fragment in col_lower:
                raise PrivacyViolationError(
                    f"Column '{col.key}' contains forbidden privacy fragment "
                    f"'{fragment}'. Audio and voice-derived data must never be "
                    "stored in the database."
                )


# ---------------------------------------------------------------------------
# 1. ChildProfile
# ---------------------------------------------------------------------------

class ChildProfile(Base):
    """
    Pseudonymous child reference.
    Real names, device IDs, and biometric identifiers are never stored.
    """

    __tablename__ = "child_profile"

    pseudonym_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid4
    )
    consent_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="child", cascade="all, delete-orphan"
    )
    consent_records: Mapped[list["ConsentRecord"]] = relationship(
        back_populates="child", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 2. ExercisePlan
# ---------------------------------------------------------------------------

class ExercisePlan(Base):
    """
    Therapist-authored exercise plan downloaded from the therapist backend.
    exercises_json stores a JSON array of exercise descriptors (IDs, words, etc.)
    """

    __tablename__ = "exercise_plan"

    plan_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid4
    )
    therapist_ref: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="Opaque therapist/clinic reference — no PII"
    )
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    plan_version: Mapped[str] = mapped_column(String(32), nullable=False)
    exercises_json: Mapped[str] = mapped_column(
        Text, nullable=False, comment="JSON array of exercise descriptors"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="plan")


# ---------------------------------------------------------------------------
# 3. Session
# ---------------------------------------------------------------------------

class Session(Base):
    """One therapy session for one child."""

    __tablename__ = "session"
    __table_args__ = (
        Index("ix_session_pseudonym", "pseudonym_id"),
        Index("ix_session_status", "status"),
    )

    session_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid4
    )
    pseudonym_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("child_profile.pseudonym_id"), nullable=False
    )
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("exercise_plan.plan_id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active",
        comment="active | completed | cancelled | error"
    )
    # Aggregates updated at session end
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    total_exercises: Mapped[int] = mapped_column(Integer, default=0)

    child: Mapped[ChildProfile] = relationship(back_populates="sessions")
    plan: Mapped[ExercisePlan] = relationship(back_populates="sessions")
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 4. Attempt
# ---------------------------------------------------------------------------

class Attempt(Base):
    """
    One pronunciation attempt within a session.

    NOTE: capture_status carries only structured status codes.
    Raw audio, MFCC, embeddings, and phoneme-probability sequences
    are NEVER stored in this or any other table.
    """

    __tablename__ = "attempt"
    __table_args__ = (Index("ix_attempt_session", "session_id"),)

    attempt_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid4
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("session.session_id"), nullable=False
    )
    exercise_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_word: Mapped[str] = mapped_column(String(128), nullable=False)

    # Status codes from Member 1 capture validation
    capture_status: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="valid | silence | clipped | too_short | timeout | cancelled"
    )

    # Version traceability (required by §6.2 invariant 7)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    dict_version: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)

    # Decision outcome
    decision: Mapped[str] = mapped_column(
        String(32), nullable=False,
        comment="pass | targeted_coaching | retry | break | no_response | escalate"
    )
    response_intent: Mapped[str] = mapped_column(String(64), nullable=False)

    # Alignment summary (no raw data)
    alignment_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    overall_gop_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    sync_eligible: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped[Session] = relationship(back_populates="attempts")
    phoneme_scores: Mapped[list["PhonemeScore"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )
    syllable_scores: Mapped[list["SyllableScore"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# 5. PhonemeScore
# ---------------------------------------------------------------------------

class PhonemeScore(Base):
    """GOP score for a single phoneme in one attempt."""

    __tablename__ = "phoneme_score"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("attempt.attempt_id"), nullable=False
    )
    phoneme: Mapped[str] = mapped_column(String(16), nullable=False)
    gop: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="pass | coach | retry"
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, comment="0-indexed position in word")

    attempt: Mapped[Attempt] = relationship(back_populates="phoneme_scores")


# ---------------------------------------------------------------------------
# 6. SyllableScore
# ---------------------------------------------------------------------------

class SyllableScore(Base):
    """Aggregated score for a syllable in one attempt."""

    __tablename__ = "syllable_score"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("attempt.attempt_id"), nullable=False
    )
    syllable: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="pass | coach | retry"
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    attempt: Mapped[Attempt] = relationship(back_populates="syllable_scores")


# ---------------------------------------------------------------------------
# 7. ModelVersionLog
# ---------------------------------------------------------------------------

class ModelVersionLog(Base):
    """Tracks which model/dictionary/policy versions were active at load time."""

    __tablename__ = "model_version_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    component: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="acoustic_model | phoneme_ctc | pronunciation_dict | policy"
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )


# ---------------------------------------------------------------------------
# 8. ConsentRecord
# ---------------------------------------------------------------------------

class ConsentRecord(Base):
    """Tracks consent grants and revocations per child."""

    __tablename__ = "consent_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pseudonym_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("child_profile.pseudonym_id"), nullable=False
    )
    consent_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="local_processing | metric_sync | therapist_review"
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)

    child: Mapped[ChildProfile] = relationship(back_populates="consent_records")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


# ---------------------------------------------------------------------------
# 9. AuditEvent
# ---------------------------------------------------------------------------

class AuditEvent(Base):
    """
    Append-only audit log.
    detail_json must NOT contain audio, embeddings, PII, or forbidden fields.
    """

    __tablename__ = "audit_event"

    event_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid4
    )
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="session_start | session_end | attempt | consent_grant | sync_sent | error"
    )
    pseudonym_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    detail_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Structured summary only — no raw audio, no child PII, no embeddings"
    )


# ---------------------------------------------------------------------------
# 10. SyncQueue
# ---------------------------------------------------------------------------

class SyncQueue(Base):
    """
    Outbound metric sync queue.
    payload_json is validated against the allow-list before insertion.
    """

    __tablename__ = "sync_queue"

    entry_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid4
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True,
        comment="Stable key to prevent duplicate sync on retry"
    )
    payload_json: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Allow-listed metric payload — validated before insertion"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending",
        comment="pending | sent | failed | skipped"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, nullable=False
    )
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------------------
# Register privacy guard on all tables
# ---------------------------------------------------------------------------

for _model_class in Base.__subclasses__():
    event.listen(_model_class, "before_insert", _check_column_names)
