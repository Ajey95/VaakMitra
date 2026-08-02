"""Structured Member 2 pronunciation evidence consumed by Member 3."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ScoreStatus = Literal["pass", "coach", "retry", "unscorable"]
AssessmentStatus = Literal["ok", "retry", "unscorable", "error"]


class PhonemeScore(BaseModel):
    """Traceable pronunciation evidence for one aligned expected phoneme."""

    model_config = ConfigDict(frozen=True)

    phoneme: str = Field(min_length=1)
    gop: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    status: ScoreStatus
    start_ms: float = Field(ge=0)
    end_ms: float = Field(gt=0)
    reason: str | None = None


class SyllableScore(BaseModel):
    """Duration-weighted aggregate that retains its source phoneme indices."""

    model_config = ConfigDict(frozen=True)

    syllable: str = Field(min_length=1)
    score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    status: ScoreStatus
    phoneme_indices: tuple[int, ...]


class AssessmentResult(BaseModel):
    """Privacy-safe, JSON-compatible Member 2 attempt result."""

    model_config = ConfigDict(frozen=True)

    attempt_id: str = Field(min_length=1)
    status: AssessmentStatus
    model_version: str = Field(min_length=1)
    vocabulary_version: str = Field(min_length=1)
    scoring_version: str = Field(min_length=1)
    phoneme_scores: tuple[PhonemeScore, ...] = ()
    syllable_scores: tuple[SyllableScore, ...] = ()
    overall_confidence: float = Field(ge=0, le=1)
    reason: str | None = None

