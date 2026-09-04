"""
Pydantic schemas for the session API.

These are the typed contracts between Unity (C# HTTP client) and the
ASD-Edge-ST backend. All shapes must be kept stable — breaking changes
require a version bump and migration plan.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

class SessionStartRequest(BaseModel):
    """Unity → backend: start a new therapy session."""
    pseudonym_id: str = Field(description="Child pseudonym UUID")
    plan_id: str = Field(description="Exercise plan ID to use for this session")


class SessionStartResponse(BaseModel):
    """backend → Unity: session started confirmation."""
    session_id: str
    plan_id: str
    status: str = "active"
    first_exercise_id: str
    first_target_word: str
    policy_version: str
    dict_version: str


# ---------------------------------------------------------------------------
# Attempt submission and result
# ---------------------------------------------------------------------------

class AttemptSubmitRequest(BaseModel):
    """
    Unity → backend: submit a child pronunciation attempt.

    audio_b64 carries the raw PCM audio bytes as base64.
    The backend processes it in memory and discards it after use.
    """
    session_id: str
    exercise_id: str
    target_word: str
    audio_b64: str = Field(
        description="Base64-encoded raw 16 kHz mono PCM audio. "
                    "Processed in memory only — never persisted."
    )


class AttemptResult(BaseModel):
    """
    backend → Unity: result of one pronunciation attempt.

    This is the primary integration contract consumed by Unity.
    It contains only approved structured fields — no raw scores,
    no embeddings, no audio data.
    """
    session_id: str
    attempt_id: str
    result: str  # pass | targeted_coaching | retry | break | no_response
    weak_unit: Optional[str] = Field(
        None,
        description="Weakest syllable (if targeted coaching), else null"
    )
    response_intent: str  # ResponseIntent enum value
    prompt_audio_id: str = Field(
        description="ID of the approved prompt audio file to play"
    )
    avatar_state: str  # AvatarState enum value
    next_exercise_id: str
    attempts_remaining: int
    persisted: bool = Field(description="True if attempt was saved to local DB")
    sync_eligible: bool = Field(
        description="True if this attempt qualifies for metric sync"
    )
    model_version: str
    dict_version: str
    policy_version: str


# ---------------------------------------------------------------------------
# Cancel / end
# ---------------------------------------------------------------------------

class CancelAttemptRequest(BaseModel):
    session_id: str
    attempt_id: Optional[str] = None
    reason: str = "user_cancelled"


class SessionEndRequest(BaseModel):
    session_id: str


class SessionEndResponse(BaseModel):
    session_id: str
    status: str  # completed | cancelled
    total_attempts: int
    total_exercises: int
    sync_queued: bool


# ---------------------------------------------------------------------------
# Health / status
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    policy_version: str
    model_version: str
    dict_version: str
    db_connected: bool
