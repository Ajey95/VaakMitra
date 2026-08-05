"""Execute the complete synthetic Member 2 model/evidence lifecycle locally."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from vaakmitra.acoustic.metadata import ModelManifest
from vaakmitra.acoustic.onnx_runtime import OnnxAcousticModelRuntime
from vaakmitra.contracts.alignment import AlignedPhoneme
from vaakmitra.ctc.vocabulary import PhonemeVocabulary

from benchmarks.run_benchmark import run_benchmark
from modeling.calibration.proxy_calibration import (
    ProxyCalibrationExample,
    calibrate_proxy_thresholds,
)
from modeling.evaluation.ctc_metrics import EvaluationRecord, evaluate_records
from modeling.fixtures.create_synthetic_ctc_onnx import create_synthetic_ctc_model
from modeling.quantization.quantize_onnx import quantize_dynamic_int8
from modeling.release.evidence import EvidenceInput, assemble_release_evidence
from modeling.validation.compare_outputs import compare_probability_outputs


@dataclass(frozen=True, slots=True)
class PrototypeFlowResult:
    fp32_model: Path
    int8_model: Path
    comparison_report: Path
    benchmark_report: Path
    evaluation_report: Path
    calibration_report: Path
    release_report: Path

    def as_dict(self) -> dict[str, str]:
        return {
            "fp32_model": str(self.fp32_model),
            "int8_model": str(self.int8_model),
            "comparison_report": str(self.comparison_report),
            "benchmark_report": str(self.benchmark_report),
            "evaluation_report": str(self.evaluation_report),
            "calibration_report": str(self.calibration_report),
            "release_report": str(self.release_report),
        }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _model_manifest(model_sha256: str, model_version: str) -> ModelManifest:
    return ModelManifest(
        schema_version="1.0",
        model_version=model_version,
        vocabulary_version="synthetic-ctc-vocab-1.0.0",
        sha256=model_sha256,
        sample_rate=16000,
        frame_shift_ms=20.0,
        blank_index=0,
        vocabulary_size=3,
        input_name="audio",
        output_name="log_probabilities",
        output_kind="log_probabilities",
    )


def run_prototype_flow(
    *,
    work_dir: str | Path,
    report_dir: str | Path,
    warmup_runs: int = 5,
    measured_runs: int = 30,
) -> PrototypeFlowResult:
    """Generate real runtime evidence using a clearly synthetic, non-Tamil model."""

    work = Path(work_dir)
    reports = Path(report_dir)
    result = PrototypeFlowResult(
        fp32_model=work / "synthetic-ctc-fp32.onnx",
        int8_model=work / "synthetic-ctc-int8.onnx",
        comparison_report=reports / "synthetic-fp32-vs-int8.json",
        benchmark_report=reports / "development-laptop-synthetic.json",
        evaluation_report=reports / "synthetic-ctc-evaluation.json",
        calibration_report=reports / "synthetic-proxy-calibration.json",
        release_report=reports / "member2-technical-prototype-evidence.json",
    )
    output_paths = (
        result.fp32_model,
        result.int8_model,
        result.comparison_report,
        result.benchmark_report,
        result.evaluation_report,
        result.calibration_report,
        result.release_report,
    )
    if any(path.exists() for path in output_paths):
        raise ValueError("prototype flow output exists; use a clean work/report directory")

    work.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    fp32_record = create_synthetic_ctc_model(result.fp32_model)
    int8_record = quantize_dynamic_int8(result.fp32_model, result.int8_model)
    fp32_manifest = _model_manifest(fp32_record.sha256, "synthetic-ctc-fp32-1.0.0")
    int8_manifest = _model_manifest(int8_record.sha256, "synthetic-ctc-int8-1.0.0")
    fp32_manifest_path = work / "synthetic-ctc-fp32.manifest.json"
    int8_manifest_path = work / "synthetic-ctc-int8.manifest.json"
    _write_json(fp32_manifest_path, fp32_manifest.model_dump(mode="json"))
    _write_json(int8_manifest_path, int8_manifest.model_dump(mode="json"))

    vocabulary = PhonemeVocabulary(
        version="synthetic-ctc-vocab-1.0.0",
        tokens=("<blank>", "a", "m"),
    )
    vocabulary_path = work / "synthetic-ctc-vocabulary.json"
    _write_json(
        vocabulary_path,
        {
            "version": vocabulary.version,
            "blank_token": vocabulary.blank_token,
            "tokens": list(vocabulary.tokens),
            "review_status": "synthetic_fixture_only_not_tamil_expert_approved",
        },
    )
    audio = np.array([0.25, -0.5, 0.75, 0.1], dtype=np.float32)
    np.save(work / "synthetic-audio.npy", audio, allow_pickle=False)

    fp32_output = OnnxAcousticModelRuntime(result.fp32_model, fp32_manifest).infer(audio, 16000)
    int8_output = OnnxAcousticModelRuntime(result.int8_model, int8_manifest).infer(audio, 16000)
    predicted_index = int(np.argmax(int8_output.log_probabilities[0]))
    predicted_token = vocabulary.token_at(predicted_index)
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
    comparison_payload = comparison.as_dict()
    comparison_payload.update(
        {
            "fp32_size_bytes": fp32_record.size_bytes,
            "int8_size_bytes": int8_record.size_bytes,
            "size_ratio_int8_to_fp32": int8_record.size_bytes / fp32_record.size_bytes,
            "evidence_scope": "synthetic_quantization_comparison",
        }
    )
    _write_json(result.comparison_report, comparison_payload)

    benchmark = run_benchmark(
        runtime_factory=lambda: OnnxAcousticModelRuntime(result.int8_model, int8_manifest),
        audio=audio,
        sample_rate=16000,
        manifest=int8_manifest,
        model_path=result.int8_model,
        provider="CPUExecutionProvider",
        evidence_scope="development_laptop",
        warmup_runs=warmup_runs,
        measured_runs=measured_runs,
    )
    _write_json(result.benchmark_report, benchmark.as_dict())

    evaluation = evaluate_records(
        (
            EvaluationRecord(
                utterance_id="synthetic-ctc-smoke-1",
                reference=("a",),
                predicted_tokens=(predicted_token,),
                blank_token=vocabulary.blank_token,
                population="adult_tamil_proxy",
                evidence_scope="engineering_proxy",
            ),
        )
    )
    _write_json(result.evaluation_report, evaluation.as_dict())
    calibration = calibrate_proxy_thresholds(
        (
            ProxyCalibrationExample("synthetic-clean", 0.9, True),
            ProxyCalibrationExample("synthetic-corrupt", 0.1, False),
            ProxyCalibrationExample("synthetic-unscorable", None, None),
        ),
        candidate_thresholds=(0.5, 0.75),
        max_false_accept_rate=0.0,
    )
    _write_json(result.calibration_report, calibration.as_dict())

    corpus_path = (
        Path(__file__).resolve().parents[1]
        / "manifests"
        / "tamil-proxy-corpus.example.json"
    )
    release = assemble_release_evidence(
        (
            EvidenceInput(
                kind="model",
                path=result.int8_model,
                evidence_scope="synthetic_fixture_model",
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
                path=result.evaluation_report,
                evidence_scope="engineering_proxy",
            ),
            EvidenceInput(
                kind="calibration",
                path=result.calibration_report,
                evidence_scope="proxy_not_therapist_calibrated",
            ),
            EvidenceInput(
                kind="comparison",
                path=result.comparison_report,
                evidence_scope="quantization_comparison",
            ),
            EvidenceInput(
                kind="benchmark",
                path=result.benchmark_report,
                evidence_scope="development_laptop",
            ),
        ),
        requested_status="technical_prototype",
    )
    _write_json(result.release_report, release.as_dict())
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the complete synthetic Member 2 edge-evidence flow locally."
    )
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--warmup-runs", type=int, default=5)
    parser.add_argument("--measured-runs", type=int, default=30)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_prototype_flow(
        work_dir=args.work_dir,
        report_dir=args.report_dir,
        warmup_runs=args.warmup_runs,
        measured_runs=args.measured_runs,
    )
    print(json.dumps(result.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
