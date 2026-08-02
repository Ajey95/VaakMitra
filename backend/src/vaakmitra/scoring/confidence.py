"""Versioned confidence calibration and neutral category gates."""

from __future__ import annotations

import math
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vaakmitra.contracts.scoring import ScoreStatus


class ScoringConfig(BaseModel):
    """Auditable baseline thresholds pending therapist-labelled calibration."""

    model_config = ConfigDict(frozen=True)

    scoring_version: str = Field(default="gop-baseline-1.0.0", min_length=1)
    min_alignment_confidence: float = Field(default=0.6, ge=0, le=1)
    acoustic_weight: float = Field(default=0.6, ge=0, le=1)
    alignment_weight: float = Field(default=0.4, ge=0, le=1)
    min_confidence: float = Field(default=0.55, ge=0, le=1)
    pass_confidence: float = Field(default=0.75, ge=0, le=1)
    coach_score: float = Field(default=0.5, ge=0, le=1)
    pass_score: float = Field(default=0.8, ge=0, le=1)

    @model_validator(mode="after")
    def validate_thresholds(self) -> Self:
        if not math.isclose(
            self.acoustic_weight + self.alignment_weight,
            1.0,
            abs_tol=1e-9,
        ):
            raise ValueError("confidence weights must sum to one")
        if self.coach_score >= self.pass_score:
            raise ValueError("coach_score must be lower than pass_score")
        if self.min_confidence >= self.pass_confidence:
            raise ValueError("min_confidence must be lower than pass_confidence")
        return self


def acoustic_separation(gop: float) -> float:
    """Map the expected-versus-competitor margin to confidence in either direction."""

    if not math.isfinite(gop) or not 0.0 <= gop <= 1.0:
        raise ValueError("gop must be finite and between zero and one")
    return abs((2.0 * gop) - 1.0)


def combine_confidence(
    *,
    gop: float,
    alignment_confidence: float,
    config: ScoringConfig,
) -> float:
    """Combine acoustic separation with forced-alignment confidence."""

    if not math.isfinite(alignment_confidence) or not 0.0 <= alignment_confidence <= 1.0:
        raise ValueError("alignment_confidence must be between zero and one")
    value = (
        config.acoustic_weight * acoustic_separation(gop)
        + config.alignment_weight * alignment_confidence
    )
    return min(1.0, max(0.0, value))


def classify_score(gop: float, confidence: float, config: ScoringConfig) -> ScoreStatus:
    """Apply confidence before score so uncertain evidence remains neutral."""

    if not math.isfinite(gop) or not 0.0 <= gop <= 1.0:
        raise ValueError("gop must be finite and between zero and one")
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be finite and between zero and one")
    if confidence < config.min_confidence:
        return "unscorable"
    if gop >= config.pass_score and confidence >= config.pass_confidence:
        return "pass"
    if gop >= config.coach_score:
        return "coach"
    return "retry"

