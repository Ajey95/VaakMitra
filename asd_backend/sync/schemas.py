"""
Pydantic schemas for metric sync and therapist API.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Outbound sync packet (device → therapist server)
# ---------------------------------------------------------------------------

class SyllableAggregate(BaseModel):
    pass_count: int
    total_count: int


class SyncPacket(BaseModel):
    """
    Privacy-safe metric packet sent to the therapist server.

    All fields are explicitly listed. No audio, embeddings, transcripts,
    raw GOP scores, or confidence values may appear here.
    """
    pseudonym_id: str
    session_id: str
    attempt_id: str
    exercise_id: str
    overall_pass: bool
    syllable_scores_aggregate: SyllableAggregate
    model_version: str
    dict_version: str
    policy_version: str
    consent_version: str
    timestamp_utc: str
    session_duration_s: Optional[float] = None


# ---------------------------------------------------------------------------
# Therapist API — exercise plan
# ---------------------------------------------------------------------------

class ExerciseDescriptor(BaseModel):
    id: str
    target_word: str
    target_phonemes: list[str]
    syllables: list[str]
    difficulty: str = "medium"


class ExercisePlanDownload(BaseModel):
    plan_id: str
    therapist_ref: str
    policy_version: str
    plan_version: str
    exercises: list[ExerciseDescriptor]


# ---------------------------------------------------------------------------
# Therapist API — analytics report
# ---------------------------------------------------------------------------

class SessionSummary(BaseModel):
    session_id: str
    started_at: str
    ended_at: Optional[str]
    total_attempts: int
    pass_rate: float


class TherapistReport(BaseModel):
    pseudonym_id: str
    sessions: list[SessionSummary]
    generated_at: str


# ---------------------------------------------------------------------------
# Sync acknowledgement (therapist server → device)
# ---------------------------------------------------------------------------

class SyncAck(BaseModel):
    received_count: int
    status: str = "ok"
    message: Optional[str] = None
