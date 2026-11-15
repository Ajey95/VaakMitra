"""Calibrated evidence fusion and fail-closed abstention (DEC-008, FUS-001..007)."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import AssessmentEvidence, AudioQuality, Decision, ReasonCode


BASE_FEATURES = {
    "p_raw_target",
    "p_normalized_target",
    "raw_normalized_disagreement",
    "p_classifier_target",
    "classifier_entropy",
    "dtw_similarity",
    "raw_top1_is_target",
    "normalized_top1_is_target",
    "duration_quality",
    "noise_quality",
}
SUPPORTED_FEATURES = BASE_FEATURES | {f"missing__{name}" for name in BASE_FEATURES}


class CalibrationArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    approved: bool = False
    model_hash: str
    classifier_hash: str
    reference_bank_hash: str
    vocabulary_hash: str
    dataset_manifest_hash: str
    vad_config_hash: str = ''
    live_pipeline_hash: str = ''  # DATA-013: empty reads old artifacts but never authorizes production.
    feature_order: tuple[str, ...]
    feature_means: tuple[float, ...]
    feature_scales: tuple[float, ...]
    coefficients: tuple[float, ...]
    intercept: float
    retry_threshold: float = Field(ge=0.0, le=1.0)
    pass_threshold: float = Field(ge=0.0, le=1.0)
    max_view_disagreement: float = Field(default=0.25, ge=0.0, le=1.0)
    population: str = "unspecified"
    model_kind: str = "logistic"
    missing_value_rule: str = "zero_after_standardization_with_explicit_mask"
    isotonic_x: tuple[float, ...] = ()
    isotonic_y: tuple[float, ...] = ()

    @model_validator(mode="after")
    def validate_shape(self) -> "CalibrationArtifact":
        size = len(self.feature_order)
        if size == 0 or len(set(self.feature_order)) != size:
            raise ValueError("feature_order must be non-empty and unique")
        if not set(self.feature_order).issubset(SUPPORTED_FEATURES):
            raise ValueError("feature_order contains unsupported features")
        if len(self.feature_means) != size or len(self.feature_scales) != size or len(self.coefficients) != size:
            raise ValueError("feature statistics and coefficients must match feature_order")
        if any(scale <= 0 for scale in self.feature_scales):
            raise ValueError("feature scales must be positive")
        if self.retry_threshold >= self.pass_threshold:
            raise ValueError("retry_threshold must be lower than pass_threshold")
        if self.model_kind not in {"logistic", "logistic_isotonic"}:
            raise ValueError("unsupported calibration model kind")
        if self.model_kind == "logistic_isotonic":
            if len(self.isotonic_x) < 2 or len(self.isotonic_x) != len(self.isotonic_y):
                raise ValueError("isotonic calibration requires paired knots")
            if any(right <= left for left, right in zip(self.isotonic_x, self.isotonic_x[1:])):
                raise ValueError("isotonic x knots must be strictly increasing")
        return self


@dataclass(frozen=True)
class FusionDecision:
    decision: Decision
    probability: float | None
    confidence: float | None
    reason_code: ReasonCode


class EvidenceCalibrator:
    def __init__(self, artifact: CalibrationArtifact):
        self.artifact = artifact

    @property
    def ready(self) -> bool:
        return self.artifact.approved

    def decide(self, evidence: AssessmentEvidence, quality: AudioQuality) -> FusionDecision:
        if not self.ready:
            return self._unscorable(ReasonCode.CALIBRATION_UNAVAILABLE)
        if not quality.valid or quality.clipped or not quality.speech_detected:
            return self._unscorable(ReasonCode.INVALID_AUDIO)

        raw = evidence.original_asr.target_probability if evidence.original_asr.available else None
        normalized = (
            evidence.normalized_asr.target_probability
            if evidence.normalized_asr.available
            else None
        )
        if raw is not None and normalized is not None:
            if abs(raw - normalized) > self.artifact.max_view_disagreement:
                return self._unscorable(ReasonCode.CROSS_VIEW_DISAGREEMENT)

        families = sum(
            (
                raw is not None or normalized is not None,
                evidence.word_classifier.available,
                evidence.embedding_dtw.available,
            )
        )
        if families < 2:
            return self._unscorable(ReasonCode.INSUFFICIENT_EVIDENCE)

        values = self.features(evidence, quality)
        standardized = []
        for name, mean, scale in zip(
            self.artifact.feature_order,
            self.artifact.feature_means,
            self.artifact.feature_scales,
            strict=True,
        ):
            value = values[name]
            standardized.append(((0.0 if value is None else value) - mean) / scale)

        logit = self.artifact.intercept + sum(
            coefficient * value
            for coefficient, value in zip(self.artifact.coefficients, standardized, strict=True)
        )
        probability = self._sigmoid(logit)
        if self.artifact.model_kind == "logistic_isotonic":
            probability = float(np.interp(probability, self.artifact.isotonic_x, self.artifact.isotonic_y))
        confidence = min(1.0, abs(probability - 0.5) * 2.0)
        if probability >= self.artifact.pass_threshold:
            return FusionDecision(Decision.PASS, probability, confidence, ReasonCode.CALIBRATED_TARGET_MATCH)
        if probability <= self.artifact.retry_threshold:
            return FusionDecision(Decision.RETRY, probability, confidence, ReasonCode.CALIBRATED_WORD_MISMATCH)
        return self._unscorable(ReasonCode.UNCERTAIN_RESULT)

    @staticmethod
    def features(evidence: AssessmentEvidence, quality: AudioQuality) -> dict[str, float | None]:
        """DEC-015: shared live and offline feature transform, including missing masks."""
        raw = evidence.original_asr.target_probability if evidence.original_asr.available else None
        normalized = evidence.normalized_asr.target_probability if evidence.normalized_asr.available else None
        values = {
            "p_raw_target": raw,
            "p_normalized_target": normalized,
            "raw_normalized_disagreement": (
                abs(raw - normalized) if raw is not None and normalized is not None else None
            ),
            "p_classifier_target": evidence.word_classifier.target_probability,
            "classifier_entropy": evidence.classifier_entropy,
            "dtw_similarity": evidence.embedding_dtw.similarity,
            "raw_top1_is_target": (
                float(evidence.original_asr.top1_is_target)
                if evidence.original_asr.top1_is_target is not None
                else None
            ),
            "normalized_top1_is_target": (
                float(evidence.normalized_asr.top1_is_target)
                if evidence.normalized_asr.top1_is_target is not None
                else None
            ),
            "duration_quality": min(1.0, quality.speech_duration_s / 0.8),
            "noise_quality": 1.0 if quality.snr_acceptable else 0.0,
        }
        values.update(
            {
                f"missing__{name}": 1.0 if value is None else 0.0
                for name, value in tuple(values.items())
            }
        )
        return values

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0:
            return 1.0 / (1.0 + exp(-value))
        positive = exp(value)
        return positive / (1.0 + positive)

    @staticmethod
    def _unscorable(reason: ReasonCode) -> FusionDecision:
        return FusionDecision(Decision.UNSCORABLE, None, None, reason)
