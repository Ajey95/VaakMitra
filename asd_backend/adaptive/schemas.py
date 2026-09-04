"""
Pydantic schemas for the adaptive engine inputs and outputs.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Inputs — received from Member 2's GOP scorer
# ---------------------------------------------------------------------------

class PhonemeScoreInput(BaseModel):
    phoneme: str
    gop: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    status: str  # "pass" | "coach" | "retry"


class SyllableScoreInput(BaseModel):
    syllable: str
    score: float = Field(ge=0.0, le=1.0)
    status: str  # "pass" | "coach" | "retry"


class ScoringResult(BaseModel):
    """Full scoring payload from Member 2 for one attempt."""

    attempt_id: str
    model_version: str
    phoneme_scores: list[PhonemeScoreInput]
    syllable_scores: list[SyllableScoreInput]
    overall_confidence: float = Field(ge=0.0, le=1.0)


class SessionState(BaseModel):
    """State tracked by the session orchestrator for one session."""

    session_id: str
    exercise_id: str
    target_word: str
    attempt_count: int = Field(ge=0, description="Attempts at the current exercise so far")
    consecutive_retries: int = Field(ge=0)
    session_attempt_count: int = Field(ge=0, description="Total attempts across session")
    no_response_count: int = Field(ge=0)
    capture_status: str = Field(
        description="valid | silence | clipped | too_short | timeout | cancelled"
    )
    next_exercise_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Outputs — fed to Unity and persisted
# ---------------------------------------------------------------------------

class ResponseIntent(str, Enum):
    CELEBRATE_PASS = "CELEBRATE_PASS"
    ENCOURAGE_REPEAT_SYLLABLE = "ENCOURAGE_REPEAT_SYLLABLE"
    ENCOURAGE_RETRY = "ENCOURAGE_RETRY"
    PROMPT_LOUDER = "PROMPT_LOUDER"
    OFFER_BREAK = "OFFER_BREAK"
    ESCALATE_THERAPIST = "ESCALATE_THERAPIST"
    NO_RESPONSE_PROMPT = "NO_RESPONSE_PROMPT"
    LOW_CONFIDENCE_RETRY = "LOW_CONFIDENCE_RETRY"


class AvatarState(str, Enum):
    CELEBRATE = "CELEBRATE"
    COACH = "COACH"
    NEUTRAL = "NEUTRAL"
    WAIT = "WAIT"
    CONCERNED = "CONCERNED"


class DecisionResult(BaseModel):
    """Output of the adaptive engine for one attempt."""

    attempt_id: str
    result: str  # "pass" | "targeted_coaching" | "retry" | "break" | "no_response" | "escalate"
    weak_unit: Optional[str] = Field(
        None, description="Weakest syllable identifier (if targeted coaching)"
    )
    response_intent: ResponseIntent
    avatar_state: AvatarState
    next_exercise_id: str
    attempts_remaining: int
    explanation: str = Field(description="Human-readable audit trail for the decision")
