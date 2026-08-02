"""Forced-alignment input contract owned by Member 1 and consumed by Member 2."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlignedPhoneme(BaseModel):
    """One expected phoneme aligned to a non-empty range of CTC frames."""

    model_config = ConfigDict(frozen=True)

    phoneme: str = Field(min_length=1)
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    start_ms: float = Field(ge=0)
    end_ms: float = Field(gt=0)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if self.end_frame <= self.start_frame:
            raise ValueError("end_frame must be greater than start_frame")
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class AlignmentResult(BaseModel):
    """Member 1 forced-alignment result accepted by the GOP stage."""

    model_config = ConfigDict(frozen=True)

    status: Literal["valid", "invalid"]
    confidence: float = Field(ge=0, le=1)
    phonemes: tuple[AlignedPhoneme, ...] = ()
    reason: str | None = None

    @model_validator(mode="after")
    def validate_status_payload(self) -> Self:
        if self.status == "valid" and not self.phonemes:
            raise ValueError("valid alignment requires phonemes")
        if self.status == "invalid" and not self.reason:
            raise ValueError("invalid alignment requires a reason")
        return self


class SyllableDefinition(BaseModel):
    """Maps a known syllable to ordered aligned-phoneme indices."""

    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1)
    phoneme_indices: tuple[int, ...]

    @model_validator(mode="after")
    def validate_indices(self) -> Self:
        if not self.phoneme_indices:
            raise ValueError("syllable requires at least one phoneme index")
        if any(index < 0 for index in self.phoneme_indices):
            raise ValueError("phoneme indices must be non-negative")
        if len(set(self.phoneme_indices)) != len(self.phoneme_indices):
            raise ValueError("phoneme indices must be unique")
        if tuple(sorted(self.phoneme_indices)) != self.phoneme_indices:
            raise ValueError("phoneme indices must be ordered")
        return self

