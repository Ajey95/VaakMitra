"""Wire-compatible Pydantic models owned by Member 3."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CaptureStatus(str, Enum):
    VALID = "valid"
    SILENCE = "silence"
    CLIPPED = "clipped"
    PROMPT_LEAKAGE = "prompt_leakage"
    TOO_SHORT = "too_short"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ALIGNMENT_FAILED = "alignment_failed"


class ScoreStatus(str, Enum):
    PASS = "pass"
    COACH = "coach"
    RETRY = "retry"
    UNSCORABLE = "unscorable"


class PhonemeAlignment(ContractModel):
    phoneme: str = Field(min_length=1, max_length=16)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def timestamps_are_ordered(self):
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


class AlignmentResult(ContractModel):
    contract_version: str = Field(pattern=r"^1\.\d+$")
    attempt_id: str = Field(min_length=1, max_length=64)
    capture_status: CaptureStatus
    expected_word: str = Field(min_length=1, max_length=128)
    expected_phonemes: list[str]
    phoneme_alignment: list[PhonemeAlignment]
    alignment_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    dictionary_version: str = Field(min_length=1, max_length=64)
    failure_reason: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def valid_capture_has_alignment(self):
        if self.capture_status is CaptureStatus.VALID:
            if not self.phoneme_alignment or self.alignment_confidence is None:
                raise ValueError("valid capture requires alignment and confidence")
        return self


class PhonemeScore(ContractModel):
    phoneme: str = Field(min_length=1, max_length=16)
    gop: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    status: ScoreStatus


class SyllableScore(ContractModel):
    syllable: str = Field(min_length=1, max_length=32)
    score: float = Field(ge=0.0, le=1.0)
    status: ScoreStatus


class ScoringResult(ContractModel):
    contract_version: str = Field(pattern=r"^1\.\d+$")
    attempt_id: str = Field(min_length=1, max_length=64)
    model_version: str = Field(min_length=1, max_length=64)
    phoneme_scores: list[PhonemeScore]
    syllable_scores: list[SyllableScore]
    overall_confidence: float = Field(ge=0.0, le=1.0)

