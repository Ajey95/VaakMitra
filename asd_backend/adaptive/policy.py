"""
Therapist policy configuration model.

Policy is loaded from a versioned JSON file and governs all adaptive
thresholds. Therapists can tune these values without code changes.

IMPORTANT: This policy never generates clinical diagnoses. It only
controls which pre-approved response intent and next exercise to select.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class TherapistPolicy(BaseModel):
    """
    Versioned therapist policy configuration.

    All threshold fields have conservative defaults that prioritise
    child welfare (generous pass thresholds, early breaks).
    """

    policy_version: str = Field(
        description="Semantic version string e.g. '1.0.0'"
    )

    # ── Score thresholds ──────────────────────────────────────────────────────
    phoneme_pass_gop: float = Field(
        default=0.80, ge=0.0, le=1.0,
        description="Minimum phoneme GOP to be counted as 'pass'"
    )
    syllable_pass_score: float = Field(
        default=0.75, ge=0.0, le=1.0,
        description="Minimum syllable score to be counted as 'pass'"
    )
    overall_pass_confidence: float = Field(
        default=0.80, ge=0.0, le=1.0,
        description="Minimum overall confidence for the attempt to be scoreable"
    )
    low_confidence_threshold: float = Field(
        default=0.60, ge=0.0, le=1.0,
        description="Below this confidence the attempt is marked low-confidence retry (no pronunciation judgement)"
    )

    # ── Retry / fatigue limits ────────────────────────────────────────────────
    max_retries_per_exercise: int = Field(
        default=3, ge=1,
        description="Maximum pronunciation attempts per exercise before moving on"
    )
    max_attempts_per_session: int = Field(
        default=30, ge=1,
        description="Maximum total attempts before fatigue break is triggered"
    )
    max_no_response_before_prompt: int = Field(
        default=2, ge=1,
        description="No-response events before switching to a louder prompt intent"
    )
    max_consecutive_escalate: int = Field(
        default=5, ge=1,
        description="Consecutive failed exercises before therapist escalation flag"
    )

    # ── Prompt audio mapping (intent → audio file ID) ─────────────────────────
    prompt_audio_map: dict[str, str] = Field(
        default_factory=dict,
        description="Maps ResponseIntent enum values to approved audio prompt IDs"
    )

    @classmethod
    def from_file(cls, path: Path) -> "TherapistPolicy":
        """Load and validate a policy JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def default(cls) -> "TherapistPolicy":
        """Return a safe default policy for development and testing."""
        return cls(
            policy_version="0.0.1-dev",
            prompt_audio_map={
                "CELEBRATE_PASS": "ta_celebrate_v1.wav",
                "ENCOURAGE_REPEAT_SYLLABLE": "ta_repeat_syllable_slow_v1.wav",
                "ENCOURAGE_RETRY": "ta_try_again_v1.wav",
                "PROMPT_LOUDER": "ta_speak_louder_v1.wav",
                "OFFER_BREAK": "ta_take_break_v1.wav",
                "ESCALATE_THERAPIST": "ta_wait_v1.wav",
                "NO_RESPONSE_PROMPT": "ta_i_am_listening_v1.wav",
                "LOW_CONFIDENCE_RETRY": "ta_try_again_v1.wav",
            },
        )
