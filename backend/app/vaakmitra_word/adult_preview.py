"""DEC-022: isolated adult-only diagnostic estimate; never product scoring."""

from dataclasses import dataclass
from math import isfinite

import numpy as np

from .calibration import EvidenceCalibrator
from .contracts import AssessmentEvidence, AudioQuality, ReasonCode


@dataclass(frozen=True)
class AdultPreview:
    status: str
    estimate: float | None
    reason_code: str


DEV_RETRY_MAX = 0.35
DEV_MATCH_MIN = 0.85


def adult_development_result(preview: AdultPreview) -> dict:
    """DEC-024/DDV-001..003: map adult evidence to a dev-only interaction outcome."""
    common = {
        "schema_version": "adult-development-decision-1",
        "estimate": preview.estimate,
        "band_version": "adult-dev-bands-1",
        "retry_max": DEV_RETRY_MAX,
        "match_min": DEV_MATCH_MIN,
    }
    if preview.status != "provisional" or preview.estimate is None:
        return {**common, "decision": "DEV_UNAVAILABLE", "reason_code": preview.reason_code,
                "avatar_state": "RECAPTURE"}
    if preview.estimate >= DEV_MATCH_MIN:
        decision, avatar = "DEV_MATCH", "CELEBRATE"
    elif preview.estimate <= DEV_RETRY_MAX:
        decision, avatar = "DEV_TRY_AGAIN", "ENCOURAGE_RETRY"
    else:
        decision, avatar = "DEV_UNCERTAIN", "NEUTRAL_RETRY"
    return {**common, "decision": decision,
            "reason_code": "adult_engineering_demonstration_only", "avatar_state": avatar}


def provisional_adult_estimate(calibrator: EvidenceCalibrator, evidence: AssessmentEvidence,
                               quality: AudioQuality) -> AdultPreview:
    """Replay the hash-bound feature math without changing the approved decision path."""
    artifact = calibrator.artifact
    if artifact.approved or artifact.population != "adult_only_engineering":
        return AdultPreview("unavailable", None, "adult_engineering_artifact_required")
    if not quality.valid or quality.clipped or not quality.speech_detected:
        return AdultPreview("unavailable", None, ReasonCode.INVALID_AUDIO.value)
    raw = evidence.original_asr.target_probability if evidence.original_asr.available else None
    normalized = evidence.normalized_asr.target_probability if evidence.normalized_asr.available else None
    if raw is not None and normalized is not None and abs(raw - normalized) > artifact.max_view_disagreement:
        return AdultPreview("unavailable", None, ReasonCode.CROSS_VIEW_DISAGREEMENT.value)
    families = sum((raw is not None or normalized is not None,
                    evidence.word_classifier.available, evidence.embedding_dtw.available))
    if families < 2:
        return AdultPreview("unavailable", None, ReasonCode.INSUFFICIENT_EVIDENCE.value)
    values = EvidenceCalibrator.features(evidence, quality)
    standardized = [((0.0 if values[name] is None else values[name]) - mean) / scale
                    for name, mean, scale in zip(artifact.feature_order, artifact.feature_means,
                                                 artifact.feature_scales, strict=True)]
    logit = artifact.intercept + sum(coefficient * value for coefficient, value in
                                     zip(artifact.coefficients, standardized, strict=True))
    estimate = EvidenceCalibrator._sigmoid(logit)
    if artifact.model_kind == "logistic_isotonic":
        estimate = float(np.interp(estimate, artifact.isotonic_x, artifact.isotonic_y))
    if not isfinite(estimate) or not 0.0 <= estimate <= 1.0:
        return AdultPreview("unavailable", None, "non_finite_estimate")
    return AdultPreview("provisional", estimate, "adult_engineering_only")
