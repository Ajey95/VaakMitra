"""Freeze native reference checkpoints and best-effort ONNX evidence."""

from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import torch
from pydantic import BaseModel, ConfigDict, Field, model_validator
from torch import nn

from modeling.artifacts import ArtifactRecord, describe_artifact
from modeling.export.export_onnx import export_reference_onnx

np = importlib.import_module("numpy")
onnx = importlib.import_module("onnx")
ort = importlib.import_module("onnxruntime")

ArtifactRole = Literal["head_only_candidate", "selected_reference"]
ReferenceStage = Literal["head_only", "top_encoder_blocks", "full_encoder"]
OnnxStatus = Literal["passed", "failed"]


class ReferenceArtifactManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_role: ArtifactRole
    selected_stage: ReferenceStage
    checkpoint: ArtifactRecord
    onnx: ArtifactRecord | None
    onnx_status: OnnxStatus
    onnx_failure_report: ArtifactRecord | None
    vocabulary: tuple[str, ...]
    blank_index: Literal[0] = 0
    sample_rate_hz: Literal[16000] = 16_000
    frame_subsampling: int = Field(gt=0)
    validation_metrics_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    test_metrics_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence_scope: Literal["adult_tamil_engineering_proxy"] = (
        "adult_tamil_engineering_proxy"
    )
    production_ready: Literal[False] = False

    @model_validator(mode="after")
    def validate_export_state(self) -> ReferenceArtifactManifest:
        if not self.vocabulary or self.vocabulary[0] != "<blank>":
            raise ValueError("vocabulary must begin with <blank>")
        if len(self.vocabulary) != len(set(self.vocabulary)):
            raise ValueError("vocabulary tokens must be unique")
        if self.artifact_role != "selected_reference" and self.test_metrics_sha256:
            raise ValueError("only selected_reference may bind test metrics")
        if self.onnx_status == "passed":
            if self.onnx is None or self.onnx_failure_report is not None:
                raise ValueError("passed ONNX state is inconsistent")
        elif self.onnx is not None or self.onnx_failure_report is None:
            raise ValueError("failed ONNX state is inconsistent")
        return self


@dataclass(frozen=True, slots=True)
class ReferenceExportResult:
    manifest_path: Path
    native_checkpoint_path: Path
    native_checkpoint_preserved: bool
    onnx_status: OnnxStatus
    onnx_path: Path | None
    failure_report_path: Path | None


def _write_json_exclusive(path: Path, payload: Mapping[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, sort_keys=True, separators=(",", ":"))
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    return path


def _copy_exclusive(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as input_file, destination.open("xb") as output_file:
        shutil.copyfileobj(input_file, output_file, length=1024 * 1024)
        output_file.flush()
        os.fsync(output_file.fileno())


def _validate_onnx_parity(model: nn.Module, onnx_path: Path) -> None:
    onnx.checker.check_model(onnx.load(str(onnx_path)))
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    for sample_count in (16_000, 32_000):
        audio = np.linspace(-0.25, 0.25, sample_count, dtype=np.float32)[None, :]
        lengths = np.asarray([sample_count], dtype=np.int64)
        candidate_logits, candidate_lengths = session.run(
            None,
            {"audio": audio, "input_lengths": lengths},
        )
        with torch.inference_mode():
            result = model(torch.from_numpy(audio), torch.from_numpy(lengths))
        if not isinstance(result, tuple) or len(result) != 2:
            raise TypeError("reference model must return logits and frame lengths")
        reference_logits, reference_lengths = result
        reference_array = reference_logits.detach().cpu().numpy()
        reference_length_array = reference_lengths.detach().cpu().numpy()
        if candidate_logits.shape != reference_array.shape:
            raise ValueError("ONNX logit shape differs from PyTorch")
        if not np.array_equal(candidate_lengths, reference_length_array):
            raise ValueError("ONNX frame lengths differ from PyTorch")
        if not np.isfinite(candidate_logits).all() or not np.isfinite(reference_array).all():
            raise ValueError("reference parity values must be finite")
        if not np.allclose(candidate_logits, reference_array, rtol=1e-4, atol=1e-5):
            raise ValueError("ONNX logits differ from PyTorch")


def _failure_report(
    path: Path,
    *,
    error: Exception,
    checkpoint: ArtifactRecord,
    binding_sha256: str,
) -> ArtifactRecord:
    _write_json_exclusive(
        path,
        {
            "binding_sha256": binding_sha256,
            "checkpoint_sha256": checkpoint.sha256,
            "environment": {
                "cuda": torch.version.cuda,
                "onnx": onnx.__version__,
                "onnxruntime": ort.__version__,
                "python": platform.python_version(),
                "torch": torch.__version__,
            },
            "exception_type": type(error).__name__,
            "failure_code": "reference_onnx_export_failed",
        },
    )
    return describe_artifact(path)


def export_reference_candidate(
    *,
    model: nn.Module,
    native_checkpoint: Path,
    output_dir: Path,
    tokens: tuple[str, ...],
    run_binding: Mapping[str, object],
    artifact_role: ArtifactRole,
    selected_stage: ReferenceStage,
    validation_metrics_path: Path,
    test_metrics_path: Path | None,
    sample_rate_hz: int,
    frame_subsampling: int,
) -> ReferenceExportResult:
    """Freeze a native checkpoint, then attempt and validate ONNX independently."""

    binding_sha256 = run_binding.get("binding_sha256")
    if not isinstance(binding_sha256, str):
        raise TypeError("run binding must contain binding_sha256")
    if artifact_role != "selected_reference" and test_metrics_path is not None:
        raise ValueError("only selected_reference may bind test metrics")
    if sample_rate_hz != 16_000:
        raise ValueError("reference sample rate must be 16000 Hz")
    if frame_subsampling <= 0:
        raise ValueError("frame subsampling must be positive")

    source_record = describe_artifact(native_checkpoint)
    validation_record = describe_artifact(validation_metrics_path)
    test_record = describe_artifact(test_metrics_path) if test_metrics_path else None
    output_dir.mkdir(parents=True, exist_ok=True)
    frozen_checkpoint = output_dir / "reference-native.pt"
    _copy_exclusive(native_checkpoint, frozen_checkpoint)
    checkpoint_record = describe_artifact(frozen_checkpoint)
    if checkpoint_record.sha256 != source_record.sha256:
        raise OSError("frozen checkpoint digest differs from selected checkpoint")

    onnx_path = output_dir / "reference.onnx"
    failure_path: Path | None = None
    onnx_record: ArtifactRecord | None = None
    failure_record: ArtifactRecord | None = None
    onnx_status: OnnxStatus
    try:
        onnx_record = export_reference_onnx(model, onnx_path)
        _validate_onnx_parity(model.cpu().eval(), onnx_path)
        onnx_status = "passed"
    # Preserve native evidence even when an exporter, checker, or runtime raises.
    except Exception as error:  # noqa: BLE001
        onnx_path.unlink(missing_ok=True)
        failure_path = output_dir / "reference-export-failure.json"
        failure_record = _failure_report(
            failure_path,
            error=error,
            checkpoint=checkpoint_record,
            binding_sha256=binding_sha256,
        )
        onnx_record = None
        onnx_status = "failed"

    manifest = ReferenceArtifactManifest(
        binding_sha256=binding_sha256,
        artifact_role=artifact_role,
        selected_stage=selected_stage,
        checkpoint=checkpoint_record,
        onnx=onnx_record,
        onnx_status=onnx_status,
        onnx_failure_report=failure_record,
        vocabulary=tokens,
        sample_rate_hz=16_000,
        frame_subsampling=frame_subsampling,
        validation_metrics_sha256=validation_record.sha256,
        test_metrics_sha256=test_record.sha256 if test_record else None,
    )
    manifest_path = output_dir / "reference-artifact-manifest.json"
    _write_json_exclusive(
        manifest_path,
        manifest.model_dump(mode="json"),
    )
    source_after = describe_artifact(native_checkpoint)
    preserved = source_after.sha256 == source_record.sha256
    return ReferenceExportResult(
        manifest_path=manifest_path,
        native_checkpoint_path=frozen_checkpoint,
        native_checkpoint_preserved=preserved,
        onnx_status=onnx_status,
        onnx_path=onnx_path if onnx_status == "passed" else None,
        failure_report_path=failure_path,
    )


def freeze_reference_evidence(
    output_path: Path,
    *,
    binding_sha256: str,
    artifacts: Mapping[str, Path],
) -> Path:
    """Write a single immutable digest inventory after final reference selection."""

    if len(binding_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in binding_sha256
    ):
        raise ValueError("binding SHA-256 must be lowercase hexadecimal")
    if not artifacts or any(not name for name in artifacts):
        raise ValueError("evidence artifacts must use non-empty names")
    records = {
        name: describe_artifact(path).as_dict()
        for name, path in sorted(artifacts.items())
    }
    return _write_json_exclusive(
        output_path,
        {
            "artifacts": records,
            "binding_sha256": binding_sha256,
            "production_ready": False,
            "schema_version": "1.0",
        },
    )
