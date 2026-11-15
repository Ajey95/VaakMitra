"""Deterministic closed-vocabulary classifier training (CLS-001..005)."""

from __future__ import annotations

import numpy as np
import pytest
import subprocess
import sys
from pathlib import Path

from app.vaakmitra_word.artifacts import _load_classifier
from app.vaakmitra_word.classifier import LinearWordClassifier
from app.vaakmitra_word.classifier_training import (
    ClassifierTrainingError,
    TrainingExample,
    pool_embedding,
    save_classifier_artifact,
    train_classifier,
)
from scripts.model.train_classifier import _active_labels


def test_mean_std_pooling_has_versioned_literal_feature_order() -> None:
    frames = np.array([[1.0, 2.0], [3.0, 6.0]], dtype=np.float32)

    pooled = pool_embedding(frames, schema="mean-std-v1")

    np.testing.assert_allclose(pooled, [2.0, 4.0, 1.0, 2.0])


def test_training_is_deterministic_balanced_and_preserves_hashes() -> None:
    examples = _examples()
    first, report = train_classifier(
        examples,
        labels=("TA_WORD_0001", "TA_WORD_0002", "OTHER"),
        model_hash="a" * 64,
        vocabulary_hash="b" * 64,
        seed=17,
    )
    second, _ = train_classifier(
        list(reversed(examples)),
        labels=("TA_WORD_0001", "TA_WORD_0002", "OTHER"),
        model_hash="a" * 64,
        vocabulary_hash="b" * 64,
        seed=17,
    )

    assert first.labels == ("TA_WORD_0001", "TA_WORD_0002", "OTHER")
    assert first.pooling_schema == "mean-std-v1"
    assert first.model_hash == "a" * 64
    assert first.vocabulary_hash == "b" * 64
    np.testing.assert_allclose(first.weights, second.weights)
    np.testing.assert_allclose(first.bias, second.bias)
    assert report.train_counts == {"OTHER": 6, "TA_WORD_0001": 6, "TA_WORD_0002": 6}
    assert set(report.class_weights) == set(first.labels)
    assert report.evaluation_accuracy >= 0.95


def test_training_rejects_missing_other_class() -> None:
    with pytest.raises(ClassifierTrainingError, match="other_class_required"):
        train_classifier(
            _examples(),
            labels=("TA_WORD_0001", "TA_WORD_0002"),
            model_hash="a" * 64,
            vocabulary_hash="b" * 64,
            seed=17,
        )


def test_training_rejects_speaker_leakage_across_splits() -> None:
    examples = _examples()
    leaked = examples + [
        TrainingExample(
            sample_id="leak",
            speaker_pseudonym=examples[0].speaker_pseudonym,
            label="TA_WORD_0001",
            split="evaluation",
            embedding=np.full((3, 2), -2.0, dtype=np.float32),
        )
    ]

    with pytest.raises(ClassifierTrainingError, match="speaker_split_leakage"):
        train_classifier(
            leaked,
            labels=("TA_WORD_0001", "TA_WORD_0002", "OTHER"),
            model_hash="a" * 64,
            vocabulary_hash="b" * 64,
            seed=17,
        )


def test_binary_bootstrap_vocabulary_produces_two_explicit_rows() -> None:
    examples = [item for item in _examples() if item.label != "TA_WORD_0002"]

    artifact, report = train_classifier(
        examples,
        labels=("TA_WORD_0001", "OTHER"),
        model_hash="a" * 64,
        vocabulary_hash="b" * 64,
        seed=17,
    )

    assert artifact.weights.shape == (2, 4)
    assert artifact.bias.shape == (2,)
    assert report.evaluation_accuracy >= 0.95


def test_runtime_uses_trained_pooling_and_absent_target_fails_closed() -> None:
    artifact, _ = train_classifier(
        _examples(),
        labels=("TA_WORD_0001", "TA_WORD_0002", "OTHER"),
        model_hash="a" * 64,
        vocabulary_hash="b" * 64,
        seed=17,
    )
    classifier = LinearWordClassifier(artifact)

    result = classifier.predict(np.full((4, 2), -2.0, dtype=np.float32), "TA_WORD_0001")
    absent = classifier.predict(np.ones((4, 2), dtype=np.float32), "TA_WORD_9999")

    assert result.evidence.available is True
    assert result.candidates[0].word == "TA_WORD_0001"
    assert absent.evidence.available is False
    assert absent.evidence.reason == "target_not_in_classifier_vocabulary"


def test_trained_artifact_round_trip_preserves_preprocessing(tmp_path: Path) -> None:
    artifact, _ = train_classifier(
        _examples(),
        labels=("TA_WORD_0001", "TA_WORD_0002", "OTHER"),
        model_hash="a" * 64,
        vocabulary_hash="b" * 64,
        seed=17,
    )
    path = tmp_path / "classifier.npz"

    save_classifier_artifact(path, artifact)
    loaded = _load_classifier(path)

    assert loaded.pooling_schema == artifact.pooling_schema
    assert loaded.temperature == artifact.temperature
    np.testing.assert_allclose(loaded.feature_means, artifact.feature_means)
    np.testing.assert_allclose(loaded.feature_scales, artifact.feature_scales)


def test_classifier_training_cli_runs_directly_from_backend_root() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "scripts/model/train_classifier.py", "--help"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--embedding-root" in completed.stdout


def test_classifier_cli_reads_only_active_scoreable_registry_entries(tmp_path: Path) -> None:
    vocabulary = tmp_path / "vocabulary.json"
    vocabulary.write_text(
        '{"entries":['
        '{"word_id":"TA_WORD_0002","state":"intended","scoreable":true},'
        '{"word_id":"TA_WORD_0001","state":"active","scoreable":true},'
        '{"word_id":"TA_WORD_0003","state":"active","scoreable":false}'
        ']}',
        encoding="utf-8",
    )

    assert _active_labels(vocabulary) == ("TA_WORD_0001", "OTHER")


def _examples() -> list[TrainingExample]:
    examples: list[TrainingExample] = []
    centers = {
        "TA_WORD_0001": np.array([-2.0, 0.0]),
        "TA_WORD_0002": np.array([2.0, 0.0]),
        "OTHER": np.array([0.0, 3.0]),
    }
    split_counts = {"train": 6, "calibration": 3, "evaluation": 3}
    for label, center in centers.items():
        for split, count in split_counts.items():
            for index in range(count):
                offset = (index - count / 2) * 0.01
                frames = np.vstack((center + offset, center - offset, center))
                examples.append(
                    TrainingExample(
                        sample_id=f"{label}-{split}-{index}",
                        speaker_pseudonym=f"speaker-{label}-{split}-{index}",
                        label=label,
                        split=split,
                        embedding=frames.astype(np.float32),
                    )
                )
    return examples
