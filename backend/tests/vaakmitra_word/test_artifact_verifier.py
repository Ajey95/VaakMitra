from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import subprocess
import sys

import numpy as np

from app.vaakmitra_word.artifacts import BundleManifest, bundle_signing_input_sha256, verify_bundle
from app.vaakmitra_word.live_evidence import pipeline_fingerprint
from app.vaakmitra_word.model import ModelCapabilityError, NeMoIndicConformerAdapter
from app.vaakmitra_word.registry import build_runtime


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_bundle(tmp_path: Path, *, approved: bool = True, cross_hash: str | None = None) -> Path:
    vocabulary = {"version": "ta-core-1.0.0", "words": {"TA_00021": "அம்மா", "TA_00022": "அப்பா"}}
    vocabulary_path = tmp_path / "vocabulary.json"
    vocabulary_path.write_text(json.dumps(vocabulary, ensure_ascii=False), encoding="utf-8")
    vocabulary_hash = _hash(vocabulary_path)

    model_path = tmp_path / "indicconformer_ta.nemo"
    model_path.write_bytes(b"synthetic-never-production")
    model_hash = _hash(model_path)
    vad_path = tmp_path / 'vad-config.json'
    vad_path.write_text('{"synthetic_fixture":true}', encoding='utf-8')
    vad_hash = _hash(vad_path)

    classifier_path = tmp_path / "word_classifier.npz"
    np.savez_compressed(
        classifier_path,
        version=np.array("synthetic-classifier-1"),
        model_hash=np.array(model_hash),
        vocabulary_hash=np.array(vocabulary_hash),
        labels=np.array(["TA_00021", "TA_00022", "OTHER"]),
        weights=np.ones((3, 2), dtype=np.float32),
        bias=np.zeros(3, dtype=np.float32),
    )
    classifier_hash = _hash(classifier_path)

    reference_path = tmp_path / "reference_bank.npz"
    np.savez_compressed(
        reference_path,
        version=np.array("synthetic-references-1"),
        model_hash=np.array(model_hash),
        vocabulary_hash=np.array(vocabulary_hash),
        reference__TA_00021__0=np.ones((3, 2), dtype=np.float32),
        reference__TA_00022__0=np.full((3, 2), 0.5, dtype=np.float32),
    )
    reference_hash = _hash(reference_path)

    calibration_path = tmp_path / "calibration.json"
    calibration = {
        "version": "synthetic-calibration-1",
        "approved": approved,
        "model_hash": cross_hash or model_hash,
        "classifier_hash": classifier_hash,
        "reference_bank_hash": reference_hash,
        "vocabulary_hash": vocabulary_hash,
        "dataset_manifest_hash": "d" * 64,
        "live_pipeline_hash": pipeline_fingerprint(),
        "vad_config_hash": vad_hash,
        "feature_order": ["p_raw_target", "p_classifier_target", "dtw_similarity"],
        "feature_means": [0.5, 0.5, 0.5],
        "feature_scales": [0.25, 0.25, 0.25],
        "coefficients": [1.0, 1.0, 1.0],
        "intercept": 0.0,
        "retry_threshold": 0.35,
        "pass_threshold": 0.8,
        "max_view_disagreement": 0.25,
    }
    calibration_path.write_text(json.dumps(calibration), encoding="utf-8")

    canary_path = tmp_path / "canary.wav"
    canary_path.write_bytes(b"RIFF-synthetic-canary")

    config = {
        "schema_version": "vaakmitra-word-bundle-1",
        "deployment_mode": "synthetic_test",
        "vocabulary_version": "ta-core-1.0.0",
        "artifacts": {
            "model": {"path": model_path.name, "sha256": model_hash},
            "vocabulary": {"path": vocabulary_path.name, "sha256": vocabulary_hash},
            "classifier": {"path": classifier_path.name, "sha256": classifier_hash},
            "reference_bank": {"path": reference_path.name, "sha256": reference_hash},
            "calibration": {"path": calibration_path.name, "sha256": _hash(calibration_path)},
            "vad_config": {"path": vad_path.name, "sha256": vad_hash},
        },
        "canary": {
            "path": canary_path.name,
            "sha256": _hash(canary_path),
            "word_id": "TA_00021",
            "target_word": "அம்மா",
        },
    }
    config_path = tmp_path / "bundle.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def test_mod008_v1_engineering_bundle_never_production_ready(tmp_path):
    path = _write_bundle(tmp_path)
    manifest = json.loads(path.read_text())
    manifest['deployment_mode'] = 'engineering'
    path.write_text(json.dumps(manifest))
    result = verify_bundle(path)
    assert not result.ready
    assert 'engineering_bundle_not_production' in result.reasons


def test_missing_bundle_config_fails_closed(tmp_path: Path) -> None:
    result = verify_bundle(tmp_path / "missing.json")

    assert result.ready is False
    assert "bundle_config_unavailable" in result.reasons


def test_wrong_artifact_hash_fails_closed(tmp_path: Path) -> None:
    config_path = _write_bundle(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["artifacts"]["model"]["sha256"] = "0" * 64
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = verify_bundle(config_path)

    assert result.ready is False
    assert "model_integrity_mismatch" in result.reasons


def test_cross_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    config_path = _write_bundle(tmp_path, cross_hash="f" * 64)

    result = verify_bundle(config_path)

    assert result.ready is False
    assert "calibration_model_hash_mismatch" in result.reasons


def test_unapproved_calibration_fails_closed(tmp_path: Path) -> None:
    config_path = _write_bundle(tmp_path, approved=False)

    result = verify_bundle(config_path)

    assert result.ready is False
    assert "calibration_unapproved" in result.reasons


def test_complete_synthetic_bundle_is_engineering_ready_only(tmp_path: Path) -> None:
    config_path = _write_bundle(tmp_path)

    result = verify_bundle(config_path)

    assert result.ready is False
    assert result.engineering_ready is True
    assert result.reasons == ["synthetic_bundle_not_production"]
    assert result.versions["vocabulary"] == "ta-core-1.0.0"


def test_data013_production_bundle_rejects_unbound_or_mismatched_pipeline(tmp_path: Path) -> None:
    config_path = _write_bundle(tmp_path)
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config['deployment_mode'] = 'production'
    calibration_path = tmp_path / 'calibration.json'
    for bad_hash in (None, '0' * 64):
        calibration = json.loads(calibration_path.read_text(encoding='utf-8'))
        if bad_hash is None:
            calibration.pop('live_pipeline_hash', None)
        else:
            calibration['live_pipeline_hash'] = bad_hash
        calibration_path.write_text(json.dumps(calibration), encoding='utf-8')
        config['artifacts']['calibration']['sha256'] = _hash(calibration_path)
        config_path.write_text(json.dumps(config), encoding='utf-8')
        result = verify_bundle(config_path)
        assert result.ready is False
        assert 'calibration_live_pipeline_hash_mismatch' in result.reasons


def test_au011_production_verifier_rejects_absent_or_mismatched_vad_binding(tmp_path: Path) -> None:
    config_path = _write_bundle(tmp_path)
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config['deployment_mode'] = 'production'
    del config['artifacts']['vad_config']
    config_path.write_text(json.dumps(config), encoding='utf-8')
    assert 'calibration_vad_config_hash_mismatch' in verify_bundle(config_path).reasons
    config['artifacts']['vad_config'] = {'path': 'vad-config.json',
        'sha256': _hash(tmp_path / 'vad-config.json')}
    calibration_path = tmp_path / 'calibration.json'
    calibration = json.loads(calibration_path.read_text(encoding='utf-8'))
    calibration['vad_config_hash'] = '0' * 64
    calibration_path.write_text(json.dumps(calibration), encoding='utf-8')
    config['artifacts']['calibration']['sha256'] = _hash(calibration_path)
    config_path.write_text(json.dumps(config), encoding='utf-8')
    assert 'calibration_vad_config_hash_mismatch' in verify_bundle(config_path).reasons


def test_verified_production_bundle_still_fails_when_model_runtime_cannot_load(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = _write_bundle(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["deployment_mode"] = "production"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    def refuse_runtime(_self) -> None:
        raise ModelCapabilityError("model_runtime_unavailable: test boundary")

    monkeypatch.setattr(NeMoIndicConformerAdapter, "load", refuse_runtime)

    registry, service = build_runtime(config_path)

    assert service is None
    assert registry.scoring_readiness().ready is False
    assert "model_runtime_unavailable" in registry.scoring_readiness().reasons


def test_production_bundle_without_hashed_canary_fails_closed(tmp_path: Path) -> None:
    config_path = _write_bundle(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["deployment_mode"] = "production"
    del config["canary"]
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = verify_bundle(config_path)

    assert result.ready is False
    assert result.reasons == ["bundle_config_invalid"]


def test_v2_adult_bundle_is_engineering_ready_but_never_scoring_ready(tmp_path: Path) -> None:
    config_path = _write_engineering_v2_bundle(tmp_path)

    result = verify_bundle(config_path)

    assert result.engineering_ready is True
    assert result.ready is False
    assert "engineering_bundle_not_production" in result.reasons
    assert "calibration_unapproved" in result.reasons
    assert "canary_human_unapproved" in result.reasons


def test_gov004_engineering_bundle_can_stage_canary_before_technical_run(tmp_path: Path) -> None:
    config_path = _write_engineering_v2_bundle(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    del config["artifacts"]["canary_run"]
    parsed = BundleManifest.model_validate(config)
    config["release"]["signing_input_sha256"] = bundle_signing_input_sha256(parsed)
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = verify_bundle(config_path)

    assert result.engineering_ready is True
    assert result.ready is False
    assert "canary_technical_unavailable" in result.reasons


def test_gov004_bundle_rejects_forged_human_canary_boolean(tmp_path: Path) -> None:
    config_path = _write_engineering_v2_bundle(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    canary_path = tmp_path / "canary-suite.json"
    suite = json.loads(canary_path.read_text(encoding="utf-8"))
    suite["human_approved"] = True
    canary_path.write_text(json.dumps(suite), encoding="utf-8")
    config["artifacts"]["canary_manifest"]["sha256"] = _hash(canary_path)
    run_path = tmp_path / "canary-run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["suite_hash"] = _hash(canary_path)
    run_path.write_text(json.dumps(run), encoding="utf-8")
    config["artifacts"]["canary_run"]["sha256"] = _hash(run_path)
    config["release"]["signing_input_sha256"] = bundle_signing_input_sha256(BundleManifest.model_validate(config))
    config_path.write_text(json.dumps(config), encoding="utf-8")
    result = verify_bundle(config_path)
    assert result.ready is False
    assert "canary_human_unapproved" in result.reasons


def test_v2_dataset_manifest_is_hash_bound(tmp_path: Path) -> None:
    config_path = _write_engineering_v2_bundle(tmp_path)
    (tmp_path / "dataset-manifest.jsonl").write_text('{"changed":true}\n', encoding="utf-8")

    result = verify_bundle(config_path)

    assert result.engineering_ready is False
    assert result.reasons == ["dataset_manifest_integrity_mismatch"]


def test_v2_canary_run_must_bind_exact_suite(tmp_path: Path) -> None:
    config_path = _write_engineering_v2_bundle(tmp_path)
    run_path = tmp_path / "canary-run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["suite_hash"] = "f" * 64
    run_path.write_text(json.dumps(run), encoding="utf-8")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["artifacts"]["canary_run"]["sha256"] = _hash(run_path)
    parsed = BundleManifest.model_validate(config)
    config["release"]["signing_input_sha256"] = bundle_signing_input_sha256(parsed)
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = verify_bundle(config_path)

    assert result.engineering_ready is False
    assert result.reasons == ["canary_run_suite_hash_mismatch"]


def test_bundle_builder_cli_runs_directly_from_backend_root() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "scripts/model/build_bundle.py", "--help"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--code-commit" in completed.stdout


def _write_engineering_v2_bundle(tmp_path: Path) -> Path:
    vocabulary_path = tmp_path / "vocabulary.json"
    vocabulary_path.write_text(
        json.dumps({"version": "ta-words-v1", "words": {"TA_WORD_0001": "அம்மா"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    vocabulary_hash = _hash(vocabulary_path)
    model_path = tmp_path / "model.nemo"
    model_path.write_bytes(b"engineering-model")
    model_hash = _hash(model_path)
    dataset_path = tmp_path / "dataset-manifest.jsonl"
    dataset_path.write_text('{"sample_id":"adult-1"}\n', encoding="utf-8")
    dataset_hash = _hash(dataset_path)

    classifier_path = tmp_path / "classifier.npz"
    np.savez_compressed(
        classifier_path,
        version=np.array("classifier-v1"),
        model_hash=np.array(model_hash),
        vocabulary_hash=np.array(vocabulary_hash),
        labels=np.array(["TA_WORD_0001", "OTHER"]),
        weights=np.ones((2, 2)),
        bias=np.zeros(2),
    )
    classifier_hash = _hash(classifier_path)
    reference_path = tmp_path / "reference.npz"
    np.savez_compressed(
        reference_path,
        version=np.array("reference-v1"),
        model_hash=np.array(model_hash),
        vocabulary_hash=np.array(vocabulary_hash),
        reference__TA_WORD_0001__0=np.ones((2, 2)),
    )
    reference_hash = _hash(reference_path)
    calibration_path = tmp_path / "calibration.json"
    calibration_path.write_text(
        json.dumps({
            "version": "adult-engineering-v1", "approved": False,
            "population": "adult_only_engineering", "model_hash": model_hash,
            "classifier_hash": classifier_hash, "reference_bank_hash": reference_hash,
            "vocabulary_hash": vocabulary_hash, "dataset_manifest_hash": dataset_hash,
            "feature_order": ["p_raw_target", "p_classifier_target"],
            "feature_means": [0.5, 0.5], "feature_scales": [0.25, 0.25],
            "coefficients": [1.0, 1.0], "intercept": 0.0,
            "retry_threshold": 0.3, "pass_threshold": 0.8,
        }), encoding="utf-8",
    )
    canary_path = tmp_path / "canary-suite.json"
    canary_path.write_text(json.dumps({
        "schema_version": "vaakmitra-canary-suite-1",
        "vocabulary_hash": vocabulary_hash, "dataset_manifest_hash": dataset_hash,
        "human_approved": False,
    }), encoding="utf-8")
    canary_hash = _hash(canary_path)
    run_path = tmp_path / "canary-run.json"
    run_path.write_text(json.dumps({
        "schema_version": "vaakmitra-canary-run-1", "suite_hash": canary_hash,
        "technical_accepted": True,
    }), encoding="utf-8")

    artifacts = {
        "model": model_path, "vocabulary": vocabulary_path, "classifier": classifier_path,
        "reference_bank": reference_path, "calibration": calibration_path,
        "dataset_manifest": dataset_path, "canary_manifest": canary_path,
        "canary_run": run_path,
    }
    config = {
        "schema_version": "vaakmitra-word-bundle-2",
        "deployment_mode": "engineering",
        "vocabulary_version": "ta-words-v1",
        "artifacts": {
            name: {"path": path.name, "sha256": _hash(path)} for name, path in artifacts.items()
        },
        "release": {
            "code_commit": "1" * 40,
            "rollback_bundle_hash": "2" * 64,
            "signing_input_sha256": "3" * 64,
        },
    }
    parsed = BundleManifest.model_validate(config)
    config["release"]["signing_input_sha256"] = bundle_signing_input_sha256(parsed)
    config_path = tmp_path / "bundle.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path
