from __future__ import annotations

import numpy as np
import pytest

from app.vaakmitra_word.classifier import ClassifierArtifact, LinearWordClassifier


def test_classifier_returns_target_probability_and_other_candidate() -> None:
    artifact = ClassifierArtifact(
        version="classifier-1",
        model_hash="model-hash",
        vocabulary_hash="vocab-hash",
        labels=("TA_00021", "OTHER"),
        weights=np.array([[2.0, 0.0], [-2.0, 0.0]], dtype=np.float64),
        bias=np.zeros(2, dtype=np.float64),
    )
    classifier = LinearWordClassifier(artifact)

    result = classifier.predict(
        np.array([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32),
        word_id="TA_00021",
    )

    assert result.evidence.available is True
    assert result.evidence.target_probability is not None
    assert result.evidence.target_probability > 0.9
    assert [candidate.word for candidate in result.candidates] == ["TA_00021", "OTHER"]


def test_unknown_target_is_unavailable_not_nearest_label() -> None:
    artifact = ClassifierArtifact(
        version="classifier-1",
        model_hash="model-hash",
        vocabulary_hash="vocab-hash",
        labels=("TA_00021", "OTHER"),
        weights=np.eye(2),
        bias=np.zeros(2),
    )

    result = LinearWordClassifier(artifact).predict(np.ones((2, 2)), word_id="TA_UNKNOWN")

    assert result.evidence.available is False
    assert result.evidence.reason == "target_not_in_classifier_vocabulary"


def test_classifier_entropy_is_normalized_for_calibration_feature_contract() -> None:
    artifact = ClassifierArtifact(
        version="classifier-1",
        model_hash="model-hash",
        vocabulary_hash="vocab-hash",
        labels=("TA_00021", "TA_00022", "OTHER"),
        weights=np.zeros((3, 2)),
        bias=np.zeros(3),
    )

    result = LinearWordClassifier(artifact).predict(np.ones((2, 2)), word_id="TA_00021")

    assert result.entropy == pytest.approx(1.0)
