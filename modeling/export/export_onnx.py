"""Export an approved source checkpoint through an explicit project adapter."""

from __future__ import annotations

import argparse
import importlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from modeling.artifacts import ArtifactRecord, describe_artifact


class ExportAdapter(Protocol):
    def __call__(self, checkpoint_path: Path, output_path: Path) -> None: ...


class ExportPrerequisiteError(RuntimeError):
    """Raised when an approved checkpoint or export adapter is unavailable."""


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
