"""DEC-028/MST-006..007: mobile bundle integrity and DEV outcomes fail closed."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pytest

from app.vaakmitra_word.mobile_student_bundle import (
    BundleIntegrityError,
    MobileCalibration,
    ReferenceExample,
    build_reference_centroids,
    evaluate_development_result,
    verify_bundle,
)


def test_mst007_reference_centroids_use_distinct_speakers_and_unit_vectors() -> None:
    examples = [
        ReferenceExample("a", "s1", "TA_WORD_0001", np.asarray([1.0, 0.0])),
        ReferenceExample("b", "s1", "TA_WORD_0001", np.asarray([0.0, 1.0])),
        ReferenceExample("c", "s2", "TA_WORD_0001", np.asarray([1.0, 1.0])),
    ]
    bank = build_reference_centroids(examples, labels=("TA_WORD_0001", "OTHER"), maximum_per_target=32)
    assert bank["TA_WORD_0001"].speaker_count == 2
    assert bank["TA_WORD_0001"].sample_ids == ("a", "c")
    assert np.linalg.norm(bank["TA_WORD_0001"].centroid) == pytest.approx(1.0)


def _calibration() -> MobileCalibration:
    return MobileCalibration(
        labels=("TA_WORD_0001", "OTHER"),
        low_thresholds={"TA_WORD_0001": 0.35},
        high_thresholds={"TA_WORD_0001": 0.75},
        minimum_margin=0.10,
        minimum_similarity=0.60,
    )


@pytest.mark.parametrize(
    ("probabilities", "embedding", "vad_ok", "expected"),
    [
        ([0.95, 0.05], [1.0, 0.0], True, "DEV_MATCH"),
        ([0.10, 0.90], [0.0, 1.0], True, "DEV_TRY_AGAIN"),
        ([0.52, 0.48], [1.0, 0.0], True, "DEV_UNCERTAIN"),
        ([0.95, 0.05], [1.0, 0.0], False, "DEV_UNAVAILABLE"),
    ],
)
def test_mst007_policy_returns_exact_development_domain(
    probabilities: list[float], embedding: list[float], vad_ok: bool, expected: str
) -> None:
    result = evaluate_development_result(
        "TA_WORD_0001",
        np.asarray(probabilities),
        np.asarray(embedding),
        {"TA_WORD_0001": np.asarray([1.0, 0.0])},
        _calibration(),
        vad_ok=vad_ok,
    )
    assert result.result == expected
    assert result.word_match_probability is None


def test_mst007_unknown_target_and_non_finite_evidence_are_unavailable() -> None:
    calibration = _calibration()
    references = {"TA_WORD_0001": np.asarray([1.0, 0.0])}
    assert evaluate_development_result("MISSING", np.asarray([1.0, 0.0]), np.asarray([1.0, 0.0]), references, calibration).result == "DEV_UNAVAILABLE"
    assert evaluate_development_result("TA_WORD_0001", np.asarray([np.nan, 0.0]), np.asarray([1.0, 0.0]), references, calibration).result == "DEV_UNAVAILABLE"


def test_mst006_bundle_verifier_rejects_tampering_and_child_approval(tmp_path: Path) -> None:
    model = tmp_path / "mobile_word_student.int8.onnx"
    labels = tmp_path / "labels.json"
    references = tmp_path / "reference_bank.json"
    calibration = tmp_path / "adult_engineering_calibration.json"
    vad = tmp_path / "silero_vad.onnx"
    for path, value in [(model, b"model"), (labels, b"{}"), (references, b"{}"), (calibration, b"{}"), (vad, b"vad")]:
        path.write_bytes(value)
    files = {path.name: sha256(path.read_bytes()).hexdigest() for path in (model, labels, references, calibration, vad)}
    manifest = {
        "schema_version": "vaakmitra-mobile-bundle-1",
        "labels": ["TA_WORD_0001", "OTHER"],
        "approved_for_child_scoring": False,
        "files": files,
    }
    (tmp_path / "bundle.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert verify_bundle(tmp_path)["approved_for_child_scoring"] is False

    model.write_bytes(b"changed")
    with pytest.raises(BundleIntegrityError, match="bundle_hash_mismatch"):
        verify_bundle(tmp_path)

    model.write_bytes(b"model")
    manifest["approved_for_child_scoring"] = True
    (tmp_path / "bundle.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleIntegrityError, match="child_scoring_must_be_false"):
        verify_bundle(tmp_path)


def test_mst015_v1_bundle_rejects_mixed_architecture(tmp_path: Path) -> None:
    files: dict[str, str] = {}
    for name in (
        "mobile_word_student.int8.onnx", "labels.json", "reference_bank.json",
        "adult_engineering_calibration.json", "silero_vad.onnx",
    ):
        path = tmp_path / name
        path.write_bytes(name.encode("utf-8"))
        files[name] = sha256(path.read_bytes()).hexdigest()
    manifest = {
        "schema_version": "vaakmitra-mobile-bundle-1",
        "bundle_version": "vm-mobile-student-ta19-v1",
        "architecture_version": "raw-wave-global-pool-v0",
        "labels": ["TA_WORD_0001", "OTHER"],
        "approved_for_child_scoring": False,
        "files": files,
    }
    (tmp_path / "bundle.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BundleIntegrityError, match="bundle_architecture_mismatch"):
        verify_bundle(tmp_path)
