from __future__ import annotations

from app.vaakmitra_word.calibration import CalibrationArtifact, EvidenceCalibrator
from app.vaakmitra_word.adult_preview import AdultPreview, adult_development_result, provisional_adult_estimate
from app.vaakmitra_word.contracts import (
    AssessmentEvidence,
    AudioQuality,
    Decision,
    EvidenceItem,
    ReasonCode,
)


def artifact(*, approved: bool = True) -> CalibrationArtifact:
    return CalibrationArtifact(
        version="calibration-1",
        approved=approved,
        model_hash="model-hash",
        classifier_hash="classifier-hash",
        reference_bank_hash="reference-hash",
        vocabulary_hash="vocabulary-hash",
        dataset_manifest_hash="dataset-hash",
        feature_order=(
            "p_raw_target",
            "p_normalized_target",
            "p_classifier_target",
            "dtw_similarity",
        ),
        feature_means=(0.0, 0.0, 0.0, 0.0),
        feature_scales=(1.0, 1.0, 1.0, 1.0),
        coefficients=(2.0, 0.5, 2.0, 1.0),
        intercept=-2.5,
        retry_threshold=0.35,
        pass_threshold=0.75,
        max_view_disagreement=0.25,
    )


def good_quality() -> AudioQuality:
    return AudioQuality(
        valid=True,
        speech_detected=True,
        snr_acceptable=True,
        clipped=False,
        duration_s=1.0,
        speech_duration_s=0.8,
        rms=0.1,
        peak=0.7,
    )


def item(value: float) -> EvidenceItem:
    return EvidenceItem(available=True, target_probability=value)


def dtw(value: float) -> EvidenceItem:
    return EvidenceItem(available=True, similarity=value)


def missing(reason: str = "not_available") -> EvidenceItem:
    return EvidenceItem(available=False, reason=reason)


def test_dtw_alone_cannot_pass() -> None:
    evidence = AssessmentEvidence(
        original_asr=missing(),
        normalized_asr=missing(),
        word_classifier=missing(),
        embedding_dtw=dtw(0.99),
    )

    result = EvidenceCalibrator(artifact()).decide(evidence, good_quality())

    assert result.decision is Decision.UNSCORABLE
    assert result.reason_code is ReasonCode.INSUFFICIENT_EVIDENCE


def test_token_and_classifier_families_can_pass() -> None:
    evidence = AssessmentEvidence(
        original_asr=item(0.97),
        normalized_asr=item(0.95),
        word_classifier=item(0.96),
        embedding_dtw=dtw(0.90),
    )

    result = EvidenceCalibrator(artifact()).decide(evidence, good_quality())

    assert result.decision is Decision.PASS
    assert result.reason_code is ReasonCode.CALIBRATED_TARGET_MATCH
    assert result.probability is not None and result.probability >= 0.75


def test_low_multi_family_evidence_is_retry() -> None:
    evidence = AssessmentEvidence(
        original_asr=item(0.02),
        normalized_asr=item(0.03),
        word_classifier=item(0.01),
        embedding_dtw=dtw(0.10),
    )

    result = EvidenceCalibrator(artifact()).decide(evidence, good_quality())

    assert result.decision is Decision.RETRY
    assert result.reason_code is ReasonCode.CALIBRATED_WORD_MISMATCH


def test_invalid_audio_is_unscorable() -> None:
    quality = good_quality().model_copy(update={"valid": False, "clipped": True})

    result = EvidenceCalibrator(artifact()).decide(AssessmentEvidence(), quality)

    assert result.decision is Decision.UNSCORABLE
    assert result.reason_code is ReasonCode.INVALID_AUDIO


def test_original_and_normalized_disagreement_blocks_pass() -> None:
    evidence = AssessmentEvidence(
        original_asr=item(0.95),
        normalized_asr=item(0.20),
        word_classifier=item(0.99),
        embedding_dtw=dtw(0.95),
    )

    result = EvidenceCalibrator(artifact()).decide(evidence, good_quality())

    assert result.decision is Decision.UNSCORABLE
    assert result.reason_code is ReasonCode.CROSS_VIEW_DISAGREEMENT


def test_unapproved_artifact_cannot_score() -> None:
    calibrator = EvidenceCalibrator(artifact(approved=False))

    assert calibrator.ready is False
    assert calibrator.decide(AssessmentEvidence(), good_quality()).reason_code is ReasonCode.CALIBRATION_UNAVAILABLE


def test_dec022_adult_preview_uses_same_fusion_without_promoting_official_decision() -> None:
    calibrator = EvidenceCalibrator(artifact(approved=False).model_copy(update={"population": "adult_only_engineering"}))
    evidence = AssessmentEvidence(original_asr=item(0.97), normalized_asr=item(0.95),
                                  word_classifier=item(0.96), embedding_dtw=dtw(0.90))
    expected = EvidenceCalibrator(artifact()).decide(evidence, good_quality()).probability

    preview = provisional_adult_estimate(calibrator, evidence, good_quality())

    assert preview.estimate == expected
    assert preview.status == "provisional"
    assert calibrator.decide(evidence, good_quality()).probability is None


def test_dec022_adult_preview_abstains_on_invalid_uncertain_or_wrong_population() -> None:
    calibrator = EvidenceCalibrator(artifact(approved=False).model_copy(update={"population": "adult_only_engineering"}))
    strong = AssessmentEvidence(original_asr=item(0.97), normalized_asr=item(0.95),
                                word_classifier=item(0.96), embedding_dtw=dtw(0.90))
    assert provisional_adult_estimate(calibrator, strong, good_quality().model_copy(update={"valid": False})).estimate is None
    assert provisional_adult_estimate(calibrator, AssessmentEvidence(original_asr=item(0.95),
        normalized_asr=item(0.20), word_classifier=item(0.99), embedding_dtw=dtw(0.95)), good_quality()).estimate is None
    assert provisional_adult_estimate(calibrator, AssessmentEvidence(embedding_dtw=dtw(0.99)), good_quality()).estimate is None
    assert provisional_adult_estimate(EvidenceCalibrator(artifact(approved=False)), strong, good_quality()).estimate is None


def test_dec024_development_result_maps_all_actionable_bands_and_boundaries() -> None:
    cases = (
        (0.35, "DEV_TRY_AGAIN", "ENCOURAGE_RETRY"),
        (0.350001, "DEV_UNCERTAIN", "NEUTRAL_RETRY"),
        (0.849999, "DEV_UNCERTAIN", "NEUTRAL_RETRY"),
        (0.85, "DEV_MATCH", "CELEBRATE"),
    )
    for estimate, decision, avatar in cases:
        result = adult_development_result(AdultPreview("provisional", estimate, "adult_engineering_only"))
        assert result == {
            "schema_version": "adult-development-decision-1",
            "decision": decision,
            "estimate": estimate,
            "reason_code": "adult_engineering_demonstration_only",
            "avatar_state": avatar,
            "band_version": "adult-dev-bands-1",
            "retry_max": 0.35,
            "match_min": 0.85,
        }


def test_dec024_development_result_never_invents_a_missing_estimate() -> None:
    result = adult_development_result(AdultPreview("unavailable", None, "INVALID_AUDIO"))
    assert result["decision"] == "DEV_UNAVAILABLE"
    assert result["estimate"] is None
    assert result["reason_code"] == "INVALID_AUDIO"
    assert result["avatar_state"] == "RECAPTURE"

