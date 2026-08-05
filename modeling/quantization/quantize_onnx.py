"""Create a separate dynamic-INT8 ONNX artifact for measured comparison."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from modeling.artifacts import ArtifactRecord, describe_artifact


class NumpyCalibrationReader:
    """Finite, in-memory calibration adapter for optional static ONNX INT8."""

    def __init__(self, samples: Sequence[Mapping[str, npt.NDArray[Any]]]) -> None:
        if not samples:
            raise ValueError("static calibration requires at least one sample")
        for sample in samples:
            if not sample:
                raise ValueError("calibration samples must contain model inputs")
            for name, array in sample.items():
                if not name or any(term in name.casefold() for term in ("path", "transcript")):
                    raise ValueError("calibration input names must be non-sensitive")
                if not isinstance(array, np.ndarray) or array.size == 0:
                    raise TypeError("calibration inputs must be non-empty NumPy arrays")
                if np.issubdtype(array.dtype, np.floating) and not np.isfinite(array).all():
                    raise ValueError("calibration inputs must contain only finite values")
        self._samples = tuple(samples)
        self._index = 0

    def get_next(self) -> Mapping[str, npt.NDArray[Any]] | None:
        if self._index >= len(self._samples):
            return None
        sample = self._samples[self._index]
        self._index += 1
        return sample

    def rewind(self) -> None:
        self._index = 0


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
