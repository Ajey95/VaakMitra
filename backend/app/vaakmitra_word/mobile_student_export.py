"""ONNX export, static quantization and parity gates for DEC-028/MST-005."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.quantization import CalibrationDataReader, CalibrationMethod, QuantFormat, QuantType, quantize_static
import torch

from .mobile_student_model import MobileWordStudent


class QuantizationGateError(RuntimeError):
    """The INT8 model is not numerically equivalent enough to integrate."""


class ArrayCalibrationReader(CalibrationDataReader):
    def __init__(self, waveforms: Iterable[np.ndarray]) -> None:
        self._values = [np.asarray(value, dtype=np.float32) for value in waveforms]
        self._index = 0

    def get_next(self) -> dict[str, np.ndarray] | None:
        if self._index >= len(self._values):
            return None
        value = self._values[self._index]
        self._index += 1
        return {"waveform": value}

    def rewind(self) -> None:
        self._index = 0


@dataclass(frozen=True)
class QuantizationParity:
    top1_agreement: float
    actionable_top1_agreement: float
    actionable_samples: int
    actionable_coverage: float
    probability_mae: float
    fp32_macro_f1: float
    int8_macro_f1: float
    macro_f1_loss: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def require_mobile_candidate_gate(
    parity: QuantizationParity,
    *,
    minimum_int8_macro_f1: float = 0.30,
) -> None:
    """MST-014: parity alone cannot promote a weak clean-evaluation model."""
    if parity.int8_macro_f1 < minimum_int8_macro_f1:
        raise QuantizationGateError(
            f"adult_int8_macro_f1:{parity.int8_macro_f1:.6f}<{minimum_int8_macro_f1:.2f}"
        )


def export_fp32_onnx(model: MobileWordStudent, destination: Path | str) -> None:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    model = model.cpu().eval()
    torch.onnx.export(
        model,
        torch.zeros((1, 32_000), dtype=torch.float32),
        path,
        input_names=["waveform"],
        output_names=["embedding", "logits"],
        dynamic_axes={"waveform": {0: "batch"}, "embedding": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
        do_constant_folding=True,
        # MST-005: retain the qualified TorchScript exporter when PyTorch defaults change.
        dynamo=False,
    )
    onnx.checker.check_model(onnx.load(path))


def quantize_int8_onnx(
    source: Path | str,
    destination: Path | str,
    reader: CalibrationDataReader,
    *,
    nodes_to_exclude: tuple[str, ...] = (),
    nodes_to_quantize: tuple[str, ...] = (),
) -> None:
    quantize_static(
        model_input=str(source),
        model_output=str(destination),
        calibration_data_reader=reader,
        quant_format=QuantFormat.QDQ,
        activation_type=QuantType.QInt8,
        weight_type=QuantType.QInt8,
        per_channel=True,
        calibrate_method=CalibrationMethod.Percentile,
        nodes_to_exclude=list(nodes_to_exclude),
        nodes_to_quantize=list(nodes_to_quantize),
        extra_options={"CalibPercentile": 99.99},
    )
    onnx.checker.check_model(onnx.load(destination))


def run_onnx(model_path: Path | str, waveforms: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    embedding, logits = session.run(
        ["embedding", "logits"],
        {"waveform": np.asarray(waveforms, dtype=np.float32)},
    )
    return np.asarray(embedding), np.asarray(logits)


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    values = np.exp(shifted)
    return values / np.sum(values, axis=1, keepdims=True)


def _macro_f1(actual: np.ndarray, predicted: np.ndarray) -> float:
    labels = np.unique(actual)
    scores: list[float] = []
    for label in labels:
        true_positive = int(np.sum((actual == label) & (predicted == label)))
        false_positive = int(np.sum((actual != label) & (predicted == label)))
        false_negative = int(np.sum((actual == label) & (predicted != label)))
        denominator = 2 * true_positive + false_positive + false_negative
        scores.append(0.0 if denominator == 0 else (2 * true_positive) / denominator)
    return float(np.mean(scores)) if scores else 0.0


def assess_quantization_parity(
    fp32_logits: np.ndarray,
    int8_logits: np.ndarray,
    actual_labels: np.ndarray,
) -> QuantizationParity:
    fp32 = np.asarray(fp32_logits, dtype=np.float64)
    int8 = np.asarray(int8_logits, dtype=np.float64)
    actual = np.asarray(actual_labels, dtype=np.int64)
    if fp32.shape != int8.shape or fp32.ndim != 2 or fp32.shape[0] != actual.shape[0]:
        raise QuantizationGateError("parity_shape_invalid")
    if not np.isfinite(fp32).all() or not np.isfinite(int8).all():
        raise QuantizationGateError("parity_non_finite")
    fp32_predictions = fp32.argmax(axis=1)
    int8_predictions = int8.argmax(axis=1)
    agreement = float(np.mean(fp32_predictions == int8_predictions))
    fp32_probabilities = _softmax(fp32)
    int8_probabilities = _softmax(int8)
    probability_mae = float(np.mean(np.abs(fp32_probabilities - int8_probabilities)))
    fp32_order = np.sort(fp32_probabilities, axis=1)
    int8_order = np.sort(int8_probabilities, axis=1)
    actionable = (
        (fp32_order[:, -1] - fp32_order[:, -2] >= 0.10)
        & (int8_order[:, -1] - int8_order[:, -2] >= 0.10)
    )
    actionable_samples = int(np.sum(actionable))
    if actionable_samples == 0:
        raise QuantizationGateError("actionable_region_empty")
    actionable_agreement = float(np.mean(fp32_predictions[actionable] == int8_predictions[actionable]))
    fp32_f1 = _macro_f1(actual, fp32_predictions)
    int8_f1 = _macro_f1(actual, int8_predictions)
    report = QuantizationParity(
        agreement,
        actionable_agreement,
        actionable_samples,
        actionable_samples / fp32.shape[0],
        probability_mae,
        fp32_f1,
        int8_f1,
        fp32_f1 - int8_f1,
    )
    if actionable_agreement < 0.99:
        raise QuantizationGateError(f"actionable_top1_agreement:{actionable_agreement:.6f}<0.99")
    if probability_mae > 0.02:
        raise QuantizationGateError(f"probability_mae:{probability_mae:.6f}>0.02")
    if report.macro_f1_loss > 0.01:
        raise QuantizationGateError(f"macro_f1_loss:{report.macro_f1_loss:.6f}>0.01")
    return report
