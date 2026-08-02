"""Create a separate dynamic-INT8 ONNX artifact for measured comparison."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from modeling.artifacts import ArtifactRecord, describe_artifact


def validate_quantization_paths(source_path: str | Path, output_path: str | Path) -> None:
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file():
        raise ValueError("source ONNX model is missing")
    if source.resolve() == output.resolve():
        raise ValueError("source and quantized output paths must be different")
    if output.exists():
        raise ValueError("quantized output exists; refusing to overwrite")


def quantize_dynamic_int8(
    source_path: str | Path,
    output_path: str | Path,
) -> ArtifactRecord:
    """Quantize transformer-style weights dynamically without overwriting FP32."""

    source = Path(source_path)
    output = Path(output_path)
    validate_quantization_paths(source, output)
    try:
        from onnxruntime.quantization import (  # type: ignore[import-untyped]
            QuantType,
            quantize_dynamic,
        )
    except ImportError as error:
        raise RuntimeError("onnxruntime model extra is required for quantization") from error
    output.parent.mkdir(parents=True, exist_ok=True)
    quantize_dynamic(str(source), str(output), weight_type=QuantType.QInt8)
    return describe_artifact(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a separate dynamic INT8 ONNX model for comparison.",
    )
    parser.add_argument("--input", required=True, type=Path, help="FP32 ONNX model")
    parser.add_argument("--output", required=True, type=Path, help="New INT8 ONNX model")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    record = quantize_dynamic_int8(args.input, args.output)
    print(json.dumps(record.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
