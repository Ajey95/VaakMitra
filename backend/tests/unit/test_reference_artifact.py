from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch
from modeling.export.reference_artifact import (
    ReferenceArtifactManifest,
    export_reference_candidate,
    freeze_reference_evidence,
)
from torch import nn


def _metrics(path: Path, value: float = 0.4) -> Path:
    path.write_text(json.dumps({"phoneme_error_rate": value}) + "\n", encoding="utf-8")
    return path


def test_export_failure_still_freezes_native_reference_manifest(tmp_path: Path) -> None:
    class UnsupportedFixtureModel(nn.Module):
        def forward(
            self,
            audio: torch.Tensor,
            lengths: torch.Tensor,
        ) -> tuple[torch.Tensor, torch.Tensor]:
            del audio, lengths
            raise RuntimeError("unsupported fixture export")

    native_checkpoint = tmp_path / "selected.pt"
    native_checkpoint.write_bytes(b"fixture checkpoint")
    result = export_reference_candidate(
        model=UnsupportedFixtureModel(),
        native_checkpoint=native_checkpoint,
        output_dir=tmp_path / "out",
        tokens=("<blank>", "a"),
        run_binding={"binding_sha256": "a" * 64},
        artifact_role="head_only_candidate",
        selected_stage="head_only",
        validation_metrics_path=_metrics(tmp_path / "validation.json"),
        test_metrics_path=None,
        sample_rate_hz=16_000,
        frame_subsampling=4,
    )

    assert result.native_checkpoint_preserved is True
    assert result.onnx_status == "failed"
    assert result.failure_report_path is not None
    assert result.failure_report_path.is_file()
    assert result.manifest_path.is_file()
    manifest = ReferenceArtifactManifest.model_validate_json(
        result.manifest_path.read_text(encoding="utf-8")
    )
    assert manifest.onnx is None
    assert manifest.onnx_failure_report is not None
    assert manifest.production_ready is False
    assert native_checkpoint.read_bytes() == b"fixture checkpoint"


def test_only_selected_reference_can_bind_test_metrics(tmp_path: Path) -> None:
    checkpoint = tmp_path / "selected.pt"
    checkpoint.write_bytes(b"fixture checkpoint")

    with pytest.raises(ValueError, match="selected_reference"):
        export_reference_candidate(
            model=nn.Identity(),
            native_checkpoint=checkpoint,
            output_dir=tmp_path / "out",
            tokens=("<blank>", "a"),
            run_binding={"binding_sha256": "a" * 64},
            artifact_role="head_only_candidate",
            selected_stage="head_only",
            validation_metrics_path=_metrics(tmp_path / "validation.json"),
            test_metrics_path=_metrics(tmp_path / "test.json"),
            sample_rate_hz=16_000,
            frame_subsampling=4,
        )


def test_reference_evidence_is_write_once_and_hashes_inputs(tmp_path: Path) -> None:
    checkpoint = tmp_path / "selected.pt"
    checkpoint.write_bytes(b"checkpoint")
    validation = _metrics(tmp_path / "validation.json")
    output = tmp_path / "frozen-evidence.json"

    written = freeze_reference_evidence(
        output,
        binding_sha256="b" * 64,
        artifacts={"checkpoint": checkpoint, "validation": validation},
    )
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["binding_sha256"] == "b" * 64
    assert set(payload["artifacts"]) == {"checkpoint", "validation"}
    assert all(len(item["sha256"]) == 64 for item in payload["artifacts"].values())

    with pytest.raises(FileExistsError):
        freeze_reference_evidence(
            output,
            binding_sha256="b" * 64,
            artifacts={"checkpoint": checkpoint},
        )
