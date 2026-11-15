"""Adult-only engineering calibration remains non-clinical and fail closed."""

from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path
import subprocess
import sys

from app.vaakmitra_word.calibration_training import (
    CalibrationExample,
    CalibrationTrainingError,
    train_adult_engineering_calibration,
)


HASHES = {
    "model_hash": "a" * 64,
    "classifier_hash": "b" * 64,
    "reference_bank_hash": "c" * 64,
    "vocabulary_hash": "d" * 64,
    "dataset_manifest_hash": "e" * 64,
}


def test_adult_calibration_is_deterministic_reports_metrics_and_cannot_be_approved() -> None:
    examples = _examples()
    first, report = train_adult_engineering_calibration(examples, seed=23, vad_config_hash='f' * 64, **HASHES)
    second, _ = train_adult_engineering_calibration(list(reversed(examples)), seed=23, **HASHES)

    assert first.approved is False
    assert first.vad_config_hash == 'f' * 64
    assert first.population == "adult_only_engineering"
    assert first.retry_threshold < first.pass_threshold
    assert first.feature_order == second.feature_order
    np.testing.assert_allclose(first.coefficients, second.coefficients)
    assert first.isotonic_x == second.isotonic_x
    assert "missing__p_normalized_target" in first.feature_order
    assert report.evaluation["accuracy"] >= 0.9
    assert set(report.evaluation) >= {
        "accuracy", "false_pass_rate", "false_retry_rate", "abstention_rate",
        "ece", "brier", "auroc", "auprc",
    }
    assert report.bootstrap_intervals["accuracy"][0] <= report.evaluation["accuracy"]
    assert report.bootstrap_intervals["accuracy"][1] >= report.evaluation["accuracy"]


def test_calibration_rejects_speaker_leakage() -> None:
    examples = _examples()
    examples.append(
        CalibrationExample(
            sample_id="leak",
            speaker_pseudonym=examples[0].speaker_pseudonym,
            word_id="TA_WORD_0001",
            split="evaluation",
            target_match=True,
            features=_features(0.9),
        )
    )

    with pytest.raises(CalibrationTrainingError, match="speaker_split_leakage"):
        train_adult_engineering_calibration(examples, seed=23, **HASHES)


def test_data013_training_binds_and_validates_live_pipeline_hash():
    artifact, _ = train_adult_engineering_calibration(
        _examples(), live_pipeline_hash='1' * 64, **HASHES)
    assert artifact.live_pipeline_hash == '1' * 64
    with pytest.raises(CalibrationTrainingError, match='live_pipeline_hash_invalid'):
        train_adult_engineering_calibration(_examples(), live_pipeline_hash='not-a-hash', **HASHES)


def test_calibration_requires_both_outcomes_in_every_split() -> None:
    examples = [item for item in _examples() if item.split != "evaluation" or item.target_match]

    with pytest.raises(CalibrationTrainingError, match="evaluation_missing_outcome"):
        train_adult_engineering_calibration(examples, seed=23, **HASHES)


def test_engineering_calibration_cli_runs_directly_from_backend_root() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "scripts/model/calibrate_engineering.py", "--help"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--evidence-manifest" in completed.stdout


def _features(signal: float, *, normalized_missing: bool = False) -> dict[str, float | None]:
    return {
        "p_raw_target": signal,
        "p_normalized_target": None if normalized_missing else signal - 0.01,
        "raw_normalized_disagreement": None if normalized_missing else 0.01,
        "p_classifier_target": signal - 0.02,
        "classifier_entropy": 0.1 if signal > 0.5 else 0.8,
        "dtw_similarity": signal - 0.03,
        "raw_top1_is_target": 1.0 if signal > 0.5 else 0.0,
        "normalized_top1_is_target": None if normalized_missing else (1.0 if signal > 0.5 else 0.0),
        "duration_quality": 1.0,
        "noise_quality": 1.0,
    }


def _examples() -> list[CalibrationExample]:
    rows: list[CalibrationExample] = []
    for split, count in (("train", 20), ("calibration", 12), ("evaluation", 12)):
        for target_match, base in ((False, 0.12), (True, 0.88)):
            for index in range(count):
                signal = base + (index - count / 2) * 0.002
                outcome = "match" if target_match else "wrong"
                rows.append(
                    CalibrationExample(
                        sample_id=f"{split}-{outcome}-{index}",
                        speaker_pseudonym=f"speaker-{split}-{outcome}-{index}",
                        word_id=f"TA_WORD_{index % 2 + 1:04d}",
                        split=split,
                        target_match=target_match,
                        features=_features(signal, normalized_missing=index % 5 == 0),
                    )
                )
    return rows
