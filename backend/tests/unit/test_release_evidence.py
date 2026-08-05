from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from modeling.release.assemble_evidence import main
from modeling.release.evidence import EvidenceInput, assemble_release_evidence


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _complete_inputs(
    tmp_path: Path,
    *,
    benchmark_scope: str = "development_laptop",
    corpus_scope: str = "engineering_proxy",
    evaluation_scope: str = "engineering_proxy",
    calibration_scope: str = "proxy_not_therapist_calibrated",
) -> tuple[EvidenceInput, ...]:
    model = tmp_path / "model.onnx"
    model.write_bytes(b"synthetic-onnx")
    vocabulary = _write_json(tmp_path / "vocabulary.json", {"version": "fixture-v1"})
    corpus = _write_json(tmp_path / "corpus.json", {"evidence_scope": corpus_scope})
    evaluation = _write_json(
        tmp_path / "evaluation.json",
        {"evidence_scope": evaluation_scope, "micro_per": 0.2},
    )
    calibration = _write_json(
        tmp_path / "calibration.json",
        {"calibration_status": calibration_scope},
    )
    comparison = _write_json(
        tmp_path / "comparison.json",
        {"max_probability_delta": 0.01},
    )
    benchmark = _write_json(
        tmp_path / "benchmark.json",
        {"evidence_scope": benchmark_scope, "latency": {"p95_ms": 10.0}},
    )
    return (
        EvidenceInput(kind="model", path=model, evidence_scope="model_artifact"),
        EvidenceInput(
            kind="vocabulary", path=vocabulary, evidence_scope="vocabulary_artifact"
        ),
        EvidenceInput(kind="corpus", path=corpus, evidence_scope=corpus_scope),
        EvidenceInput(
            kind="evaluation", path=evaluation, evidence_scope=evaluation_scope
        ),
        EvidenceInput(
            kind="calibration", path=calibration, evidence_scope=calibration_scope
        ),
        EvidenceInput(
            kind="comparison",
            path=comparison,
            evidence_scope="quantization_comparison",
        ),
        EvidenceInput(
            kind="benchmark", path=benchmark, evidence_scope=benchmark_scope
        ),
    )


def test_prototype_bundle_hashes_every_required_input_without_absolute_paths(
    tmp_path: Path,
) -> None:
    report = assemble_release_evidence(
        _complete_inputs(tmp_path),
        requested_status="technical_prototype",
    )

    assert report.release_status == "technical_prototype"
    assert {artifact.kind for artifact in report.artifacts} == {
        "model",
        "vocabulary",
        "corpus",
        "evaluation",
        "calibration",
        "comparison",
        "benchmark",
    }
    model = next(artifact for artifact in report.artifacts if artifact.kind == "model")
    assert model.sha256 == hashlib.sha256(b"synthetic-onnx").hexdigest()
    assert model.filename == "model.onnx"
    assert str(tmp_path) not in json.dumps(report.as_dict())
    assert "no therapist-labelled target-user evidence" in report.limitations
    assert "no actual target-device benchmark" in report.limitations


def test_release_evidence_rejects_missing_or_duplicate_required_kind(tmp_path: Path) -> None:
    inputs = _complete_inputs(tmp_path)

    with pytest.raises(ValueError, match="exactly one artifact"):
        assemble_release_evidence(inputs[:-1], requested_status="technical_prototype")
    with pytest.raises(ValueError, match="exactly one artifact"):
        assemble_release_evidence(
            (*inputs, inputs[0]),
            requested_status="technical_prototype",
        )


def test_release_evidence_rejects_empty_artifact(tmp_path: Path) -> None:
    inputs = list(_complete_inputs(tmp_path))
    inputs[0].path.write_bytes(b"")

    with pytest.raises(ValueError, match="non-empty"):
        assemble_release_evidence(inputs, requested_status="technical_prototype")


def test_release_evidence_rejects_declared_scope_mismatch(tmp_path: Path) -> None:
    inputs = list(_complete_inputs(tmp_path))
    benchmark = inputs[-1]
    inputs[-1] = benchmark.model_copy(update={"evidence_scope": "target_device"})

    with pytest.raises(ValueError, match="embedded evidence scope"):
        assemble_release_evidence(inputs, requested_status="technical_prototype")


def test_target_device_release_rejects_laptop_benchmark(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="actual target_device"):
        assemble_release_evidence(
            _complete_inputs(tmp_path),
            requested_status="target_device_validated",
        )


def test_target_device_release_rejects_proxy_evaluation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="target_user_validation"):
        assemble_release_evidence(
            _complete_inputs(tmp_path, benchmark_scope="target_device"),
            requested_status="target_device_validated",
        )


def test_target_device_release_rejects_proxy_calibration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="therapist_calibrated"):
        assemble_release_evidence(
            _complete_inputs(
                tmp_path,
                benchmark_scope="target_device",
                corpus_scope="target_user_validation",
                evaluation_scope="target_user_validation",
            ),
            requested_status="target_device_validated",
        )


def test_target_device_release_accepts_only_complete_external_evidence(tmp_path: Path) -> None:
    report = assemble_release_evidence(
        _complete_inputs(
            tmp_path,
            benchmark_scope="target_device",
            corpus_scope="target_user_validation",
            evaluation_scope="target_user_validation",
            calibration_scope="therapist_calibrated",
        ),
        requested_status="target_device_validated",
    )

    assert report.release_status == "target_device_validated"
    assert report.limitations == ()


def test_release_evidence_digest_is_independent_of_input_order(tmp_path: Path) -> None:
    inputs = _complete_inputs(tmp_path)

    first = assemble_release_evidence(inputs, requested_status="technical_prototype")
    second = assemble_release_evidence(
        tuple(reversed(inputs)),
        requested_status="technical_prototype",
    )

    assert first.evidence_digest == second.evidence_digest


def test_release_evidence_cli_reads_request_and_writes_report(tmp_path: Path) -> None:
    inputs = _complete_inputs(tmp_path)
    request_path = tmp_path / "request.json"
    output_path = tmp_path / "release.json"
    request_path.write_text(
        json.dumps(
            {
                "requested_status": "technical_prototype",
                "inputs": [item.model_dump(mode="json") for item in inputs],
            }
        ),
        encoding="utf-8",
    )

    assert main(["--request", str(request_path), "--output", str(output_path)]) == 0
    output = json.loads(output_path.read_text(encoding="utf-8"))

    assert output["release_status"] == "technical_prototype"
    assert len(output["artifacts"]) == 7

