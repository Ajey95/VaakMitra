"""Export an approved source checkpoint through an explicit project adapter."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import torch
from torch import nn

from modeling.artifacts import ArtifactRecord, describe_artifact
from modeling.distillation.students import StudentOutput

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ExportAdapter(Protocol):
    def __call__(self, checkpoint_path: Path, output_path: Path) -> None: ...


class ExportPrerequisiteError(RuntimeError):
    """Raised when an approved checkpoint or export adapter is unavailable."""


@dataclass(frozen=True, slots=True)
class StudentExportMetadata:
    artifact: ArtifactRecord
    config_sha256: str
    vocabulary_sha256: str
    output_kind: str
    dynamic_sample_axis: bool
    direct_text_posteriors_exported: bool


class _StudentOnnxWrapper(nn.Module):
    def __init__(self, model: nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(
        self, audio: torch.Tensor, input_lengths: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        result = self.model(audio, input_lengths)
        if not isinstance(result, StudentOutput):
            raise TypeError("student model must return StudentOutput")
        return result.logits, result.frame_lengths


def export_student_onnx(
    model: nn.Module,
    output_path: str | Path,
    *,
    example_samples: int,
    config_sha256: str,
    vocabulary_sha256: str,
) -> StudentExportMetadata:
    """Export dynamic raw-audio phoneme logits and bind model/config/vocabulary hashes."""

    if example_samples < 400:
        raise ValueError("example_samples must be at least 400")
    if not _SHA256.fullmatch(config_sha256) or not _SHA256.fullmatch(vocabulary_sha256):
        raise ValueError("config and vocabulary digests must be lowercase SHA-256")
    output = Path(output_path)
    if output.exists():
        raise ValueError("student ONNX output exists; refusing to overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    wrapper = _StudentOnnxWrapper(model.cpu().eval())
    audio = torch.zeros((1, example_samples), dtype=torch.float32)
    lengths = torch.tensor([example_samples], dtype=torch.long)
    fastpath_enabled = torch.backends.mha.get_fastpath_enabled()
    torch.backends.mha.set_fastpath_enabled(False)
    try:
        with torch.no_grad(), warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            warnings.filterwarnings("ignore", category=torch.jit.TracerWarning)
            warnings.filterwarnings("ignore", category=UserWarning)
            torch.onnx.export(
                wrapper,
                (audio, lengths),
                str(output),
                input_names=["audio", "input_lengths"],
                output_names=["phoneme_logits", "frame_lengths"],
                dynamic_axes={
                    "audio": {0: "batch", 1: "samples"},
                    "input_lengths": {0: "batch"},
                    "phoneme_logits": {0: "batch", 1: "frames"},
                    "frame_lengths": {0: "batch"},
                },
                opset_version=17,
                do_constant_folding=True,
                dynamo=False,
            )
    finally:
        torch.backends.mha.set_fastpath_enabled(fastpath_enabled)
    return StudentExportMetadata(
        artifact=describe_artifact(output),
        config_sha256=config_sha256,
        vocabulary_sha256=vocabulary_sha256,
        output_kind="phoneme_logits",
        dynamic_sample_axis=True,
        direct_text_posteriors_exported=False,
    )


def export_with_adapter(
    adapter: ExportAdapter,
    checkpoint_path: str | Path,
    output_path: str | Path,
) -> ArtifactRecord:
    """Run an explicit adapter and prove that it produced a non-empty ONNX artifact."""

    checkpoint = Path(checkpoint_path)
    output = Path(output_path)
    if not checkpoint.is_file():
        raise ExportPrerequisiteError("approved source checkpoint is missing")
    if checkpoint.resolve() == output.resolve():
        raise ExportPrerequisiteError("source checkpoint and ONNX output must be different")
    if output.exists():
        raise ExportPrerequisiteError("ONNX output already exists; refusing to overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        adapter(checkpoint, output)
    except Exception as error:
        raise ExportPrerequisiteError("source-framework export adapter failed") from error
    if not output.is_file() or output.stat().st_size == 0:
        raise ExportPrerequisiteError("export adapter did not create a non-empty ONNX file")
    return describe_artifact(output)


def load_export_adapter(specification: str) -> ExportAdapter:
    """Load `module:function` only when explicitly supplied by the model owner."""

    module_name, separator, attribute_name = specification.partition(":")
    if not separator or not module_name or not attribute_name:
        raise ExportPrerequisiteError("adapter must use module:function syntax")
    try:
        module = importlib.import_module(module_name)
        candidate = getattr(module, attribute_name)
    except (ImportError, AttributeError) as error:
        raise ExportPrerequisiteError("unable to load export adapter") from error
    if not callable(candidate):
        raise ExportPrerequisiteError("export adapter must be callable")
    return candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export an approved acoustic checkpoint through module:function adapter.",
    )
    parser.add_argument("--adapter", required=True, help="Import path in module:function form")
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    record = export_with_adapter(
        load_export_adapter(args.adapter),
        args.checkpoint,
        args.output,
    )
    print(json.dumps(record.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
