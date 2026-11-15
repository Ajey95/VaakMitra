"""Typed contracts for SSOT Sections 12 and 13 (DEC-008, FUS-001)."""

from __future__ import annotations

from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Decision(str, Enum):
    PASS = "PASS"
    RETRY = "RETRY"
    UNSCORABLE = "UNSCORABLE"


class ReasonCode(str, Enum):
    CALIBRATED_TARGET_MATCH = "CALIBRATED_TARGET_MATCH"
    CALIBRATED_WORD_MISMATCH = "CALIBRATED_WORD_MISMATCH"
    UNCERTAIN_RESULT = "UNCERTAIN_RESULT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CROSS_VIEW_DISAGREEMENT = "CROSS_VIEW_DISAGREEMENT"
    INVALID_AUDIO = "INVALID_AUDIO"
    NO_SPEECH = "NO_SPEECH"
    VAD_UNAVAILABLE = "VAD_UNAVAILABLE"
    UNSUPPORTED_AUDIO = "UNSUPPORTED_AUDIO"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_INTEGRITY_MISMATCH = "MODEL_INTEGRITY_MISMATCH"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_INFERENCE_FAILED = "MODEL_INFERENCE_FAILED"
    CLASSIFIER_UNAVAILABLE = "CLASSIFIER_UNAVAILABLE"
    REFERENCE_UNAVAILABLE = "REFERENCE_UNAVAILABLE"
    CALIBRATION_UNAVAILABLE = "CALIBRATION_UNAVAILABLE"
    ARTIFACT_MISMATCH = "ARTIFACT_MISMATCH"
    CANCELLED = "CANCELLED"


class WordCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    word: str = Field(min_length=1, max_length=128)
    probability: float = Field(ge=0.0, le=1.0)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    available: bool
    target_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    top1_is_target: bool | None = None
    reason: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_availability(self) -> "EvidenceItem":
        has_value = self.target_probability is not None or self.similarity is not None
        if self.available and not has_value:
            raise ValueError("available evidence must contain a probability or similarity")
        if not self.available and has_value:
            raise ValueError("unavailable evidence cannot contain a numeric value")
        return self


class AssessmentEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    original_asr: EvidenceItem = Field(default_factory=lambda: EvidenceItem(available=False, reason="not_run"))
    normalized_asr: EvidenceItem = Field(default_factory=lambda: EvidenceItem(available=False, reason="not_run"))
    word_classifier: EvidenceItem = Field(default_factory=lambda: EvidenceItem(available=False, reason="not_run"))
    embedding_dtw: EvidenceItem = Field(default_factory=lambda: EvidenceItem(available=False, reason="not_run"))
    classifier_entropy: float | None = Field(default=None, ge=0.0)


class AudioQuality(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: bool = False
    vad_mode: str = 'energy_degraded'
    speech_regions: list[tuple[float, float]] = Field(default_factory=list)
    speech_detected: bool = False
    snr_acceptable: bool = False
    clipped: bool = False
    duration_s: float = Field(default=0.0, ge=0.0)
    speech_duration_s: float = Field(default=0.0, ge=0.0)
    rms: float = Field(default=0.0, ge=0.0)
    peak: float = Field(default=0.0, ge=0.0)
    clipping_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str | None = None


class ModelEvidence(BaseModel):
    """Ephemeral model output. Embeddings must never be serialized to product storage."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    candidates: list[WordCandidate] = Field(default_factory=list)
    target_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    embeddings: np.ndarray | None = Field(default=None, exclude=True)
    model_version: str
    model_hash: str


class ModelReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    ready: bool
    engineering_ready: bool = False
    reasons: list[str] = Field(default_factory=list)
    model_version: str = "unavailable"
    classifier_version: str = "unavailable"
    reference_bank_version: str = "unavailable"
    calibration_version: str = "unavailable"


class AssessmentResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "3.0.0"
    session_id: str
    attempt_id: str
    word_id: str
    target_word: str
    decision: Decision
    word_match_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    observed_candidates: list[WordCandidate] = Field(default_factory=list)
    evidence: AssessmentEvidence = Field(default_factory=AssessmentEvidence)
    quality: AudioQuality = Field(default_factory=AudioQuality)
    reason_code: ReasonCode
    response_intent: str = "CAREGIVER_TECHNICAL_HELP"
    avatar_state: str = "BREAK"
    next_exercise_id: str | None = None
    model_version: str = "unavailable"
    classifier_version: str = "unavailable"
    reference_bank_version: str = "unavailable"
    calibration_version: str = "unavailable"
    policy_version: str = "ta-safe-policy-1.0.0"
    latency_ms: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_decision_probability(self) -> "AssessmentResult":
        if self.decision in (Decision.PASS, Decision.RETRY) and self.word_match_probability is None:
            raise ValueError("word_match_probability is required for PASS or RETRY")
        if self.decision is Decision.UNSCORABLE and self.word_match_probability is not None:
            raise ValueError("UNSCORABLE must not expose word_match_probability")
        return self

    @classmethod
    def unscorable(
        cls,
        reason: ReasonCode,
        *,
        session_id: str,
        attempt_id: str,
        word_id: str,
        target_word: str,
        quality: AudioQuality | None = None,
        evidence: AssessmentEvidence | None = None,
        latency_ms: int = 0,
    ) -> "AssessmentResult":
        return cls(
            session_id=session_id,
            attempt_id=attempt_id,
            word_id=word_id,
            target_word=target_word,
            decision=Decision.UNSCORABLE,
            word_match_probability=None,
            confidence=None,
            quality=quality or AudioQuality(),
            evidence=evidence or AssessmentEvidence(),
            reason_code=reason,
            latency_ms=latency_ms,
        )

    def to_legacy(self) -> dict[str, Any]:
        capability_by_reason = {
            ReasonCode.MODEL_UNAVAILABLE: "model_unavailable",
            ReasonCode.MODEL_INTEGRITY_MISMATCH: "model_unavailable",
            ReasonCode.CALIBRATION_UNAVAILABLE: "calibration_unavailable",
            ReasonCode.ARTIFACT_MISMATCH: "artifact_mismatch",
        }
        feedback_by_decision = {
            Decision.PASS: "Great listening and speaking — let’s continue!",
            Decision.RETRY: "Good try. Let’s listen and say the word once more.",
            Decision.UNSCORABLE: "I could not check that safely. Let’s try again when you are ready.",
        }
        return {
            "decision": self.decision.value,
            "matched": True if self.decision is Decision.PASS else False if self.decision is Decision.RETRY else None,
            "accuracy": (
                round(self.word_match_probability * 100.0, 2)
                if self.word_match_probability is not None
                else None
            ),
            "word_match_probability": self.word_match_probability,
            "feedback": feedback_by_decision[self.decision],
            "feedback_key": self.response_intent.lower(),
            "validation_status": self.reason_code.value,
            "capability": capability_by_reason.get(
                self.reason_code,
                "ready" if self.decision is not Decision.UNSCORABLE else "unscorable",
            ),
            "schema_version": self.schema_version,
            "model_version": self.model_version,
            "calibration_version": self.calibration_version,
        }
