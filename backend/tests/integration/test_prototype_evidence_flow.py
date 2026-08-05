from __future__ import annotations

import json

import numpy as np
import pytest
from benchmarks.run_benchmark import run_benchmark
from modeling.calibration.proxy_calibration import (
    ProxyCalibrationExample,
    calibrate_proxy_thresholds,
)
from modeling.data.corpus_manifest import CorpusManifest
from modeling.evaluation.ctc_metrics import EvaluationRecord, evaluate_records
from modeling.fixtures.create_synthetic_ctc_onnx import create_synthetic_ctc_model
from modeling.fixtures.run_prototype_flow import run_prototype_flow
from modeling.quantization.quantize_onnx import quantize_dynamic_int8
from modeling.release.evidence import EvidenceInput, assemble_release_evidence
from modeling.validation.compare_outputs import compare_probability_outputs

from vaakmitra.acoustic.metadata import ModelManifest
from vaakmitra.acoustic.onnx_runtime import OnnxAcousticModelRuntime
from vaakmitra.contracts.alignment import AlignedPhoneme
from vaakmitra.ctc.vocabulary import PhonemeVocabulary


def _write_json(path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _manifest(model_path, sha256: str, model_version: str) -> ModelManifest:
    return ModelManifest(
        schema_version="1.0",
        model_version=model_version,
        vocabulary_version="synthetic-ctc-vocab-1.0.0",
        sha256=sha256,
        sample_rate=16000,
        frame_shift_ms=20.0,
        blank_index=0,
        vocabulary_size=3,
        input_name="audio",
        output_name="log_probabilities",
        output_kind="log_probabilities",
    )


def test_synthetic_model_is_nonempty_and_reproducible(tmp_path) -> None:
    first = create_synthetic_ctc_model(tmp_path / "first.onnx")
    second = create_synthetic_ctc_model(tmp_path / "second.onnx")

    assert first.sha256 == second.sha256
    assert first.size_bytes > 0


def test_local_fp32_int8_benchmark_and_release_evidence_flow(tmp_path) -> None:
    fp32_path = tmp_path / "synthetic-fp32.onnx"
    int8_path = tmp_path / "synthetic-int8.onnx"
    fp32_record = create_synthetic_ctc_model(fp32_path)
    int8_record = quantize_dynamic_int8(fp32_path, int8_path)
    fp32_manifest = _manifest(fp32_path, fp32_record.sha256, "synthetic-ctc-fp32-1.0.0")
    int8_manifest = _manifest(int8_path, int8_record.sha256, "synthetic-ctc-int8-1.0.0")
    audio = np.array([0.25, -0.5, 0.75, 0.1], dtype=np.float32)
    vocabulary = PhonemeVocabulary(
        version="synthetic-ctc-vocab-1.0.0",
        tokens=("<blank>", "a", "m"),
    )

    fp32_output = OnnxAcousticModelRuntime(fp32_path, fp32_manifest).infer(audio, 16000)
    int8_output = OnnxAcousticModelRuntime(int8_path, int8_manifest).infer(audio, 16000)
    np.testing.assert_allclose(
        np.exp(fp32_output.log_probabilities).sum(axis=1),
        np.ones(1),
        atol=1e-6,
    )
    assert vocabulary.token_at(int(np.argmax(fp32_output.log_probabilities[0]))) == "a"

    alignment = (
        AlignedPhoneme(
            phoneme="a",
            start_frame=0,
            end_frame=1,
            start_ms=0.0,
            end_ms=20.0,
            confidence=0.95,
        ),
    )
    comparison = compare_probability_outputs(
        fp32_output.log_probabilities,
        int8_output.log_probabilities,
        alignment,
        vocabulary,
    )
    assert comparison.max_probability_delta < 0.02

    benchmark = run_benchmark(
        runtime_factory=lambda: OnnxAcousticModelRuntime(fp32_path, fp32_manifest),
        audio=audio,
        sample_rate=16000,
        manifest=fp32_manifest,
        model_path=fp32_path,
        provider="CPUExecutionProvider",
        evidence_scope="development_laptop",
        warmup_runs=1,
        measured_runs=3,
    )
    assert benchmark.latency.p95_ms >= 0.0

    corpus = CorpusManifest.model_validate(
        {
            "schema_version": "1.0",
            "dataset_id": "vaakmitra/synthetic-contract-fixtures",
            "revision": "0" * 40,
            "source_url": "https://example.invalid/vaakmitra/synthetic-contract-fixtures",
            "license_spdx": "CC0-1.0",
            "population": "adult_tamil_proxy",
            "label_origin": "rule_based_proxy",
            "evidence_scope": "engineering_proxy",
            "local_processing_only": True,
            "splits": [
                {
                    "name": "train",
                    "speakers": ["synthetic-train"],
                    "record_count": 1,
                    "index_sha256": "a" * 64,
                },
                {
                    "name": "validation",
                    "speakers": ["synthetic-validation"],
                    "record_count": 1,
                    "index_sha256": "b" * 64,
                },
                {
                    "name": "test",
                    "speakers": ["synthetic-test"],
                    "record_count": 1,
                    "index_sha256": "c" * 64,
                },
            ],
        }
    )
    evaluation = evaluate_records(
        (
            EvaluationRecord(
                utterance_id="synthetic-1",
                reference=("a",),
                predicted_tokens=("a",),
                blank_token="<blank>",
                population="adult_tamil_proxy",
                evidence_scope="engineering_proxy",
            ),
        )
    )
    calibration = calibrate_proxy_thresholds(
        (
            ProxyCalibrationExample("clean", 0.9, True),
            ProxyCalibrationExample("corrupt", 0.1, False),
        ),
        candidate_thresholds=(0.5, 0.75),
        max_false_accept_rate=0.0,
    )

    vocabulary_path = tmp_path / "vocabulary.json"
    corpus_path = tmp_path / "corpus.json"
    evaluation_path = tmp_path / "evaluation.json"
    calibration_path = tmp_path / "calibration.json"
    comparison_path = tmp_path / "comparison.json"
    benchmark_path = tmp_path / "benchmark.json"
    _write_json(
        vocabulary_path,
        {
            "version": vocabulary.version,
            "blank_token": vocabulary.blank_token,
            "tokens": list(vocabulary.tokens),
            "review_status": "synthetic_fixture_only",
        },
    )
    _write_json(corpus_path, corpus.model_dump(mode="json"))
    _write_json(evaluation_path, evaluation.as_dict())
    _write_json(calibration_path, calibration.as_dict())
    _write_json(comparison_path, comparison.as_dict())
    _write_json(benchmark_path, benchmark.as_dict())

    release = assemble_release_evidence(
        (
            EvidenceInput(
                kind="model", path=int8_path, evidence_scope="synthetic_fixture_model"
            ),
            EvidenceInput(
                kind="vocabulary",
                path=vocabulary_path,
                evidence_scope="vocabulary_artifact",
            ),
            EvidenceInput(
                kind="corpus", path=corpus_path, evidence_scope="engineering_proxy"
            ),
            EvidenceInput(
                kind="evaluation",
                path=evaluation_path,
                evidence_scope="engineering_proxy",
            ),
            EvidenceInput(
                kind="calibration",
                path=calibration_path,
                evidence_scope="proxy_not_therapist_calibrated",
            ),
            EvidenceInput(
                kind="comparison",
                path=comparison_path,
                evidence_scope="quantization_comparison",
            ),
            EvidenceInput(
                kind="benchmark",
                path=benchmark_path,
                evidence_scope="development_laptop",
            ),
        ),
        requested_status="technical_prototype",
    )

    assert release.release_status == "technical_prototype"
    assert release.validation_label == "engineering_evidence_only"
    assert release.limitations == (
        "no therapist-labelled target-user evidence",
        "no actual target-device benchmark",
        "no trained Tamil phoneme CTC model",
    )


def test_prototype_flow_command_writes_reproducible_aggregate_reports(tmp_path) -> None:
    result = run_prototype_flow(
        work_dir=tmp_path / "artifacts",
        report_dir=tmp_path / "reports",
        warmup_runs=0,
        measured_runs=2,
    )

    assert result.fp32_model.is_file()
    assert result.int8_model.is_file()
    assert result.release_report.is_file()
    release = json.loads(result.release_report.read_text(encoding="utf-8"))
    benchmark = json.loads(result.benchmark_report.read_text(encoding="utf-8"))
    comparison = json.loads(result.comparison_report.read_text(encoding="utf-8"))
    assert release["release_status"] == "technical_prototype"
    assert benchmark["evidence_scope"] == "development_laptop"
    assert comparison["max_probability_delta"] < 0.02
    assert comparison["fp32_size_bytes"] > 0
    assert comparison["int8_size_bytes"] > 0
    assert comparison["size_ratio_int8_to_fp32"] == pytest.approx(
        comparison["int8_size_bytes"] / comparison["fp32_size_bytes"]
    )
