"""DEC-028/MST-005: ONNX export and INT8 parity gates are executable."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from app.vaakmitra_word.mobile_student_export import (
    ArrayCalibrationReader,
    QuantizationGateError,
    QuantizationParity,
    assess_quantization_parity,
    export_fp32_onnx,
    quantize_int8_onnx,
    run_onnx,
    require_mobile_candidate_gate,
)
from app.vaakmitra_word.mobile_student_model import MobileWordStudent


def test_mst005_exported_model_executes_with_exact_named_shapes(tmp_path: Path) -> None:
    torch.manual_seed(3)
    model = MobileWordStudent().eval()
    model_path = tmp_path / "student.onnx"
    export_fp32_onnx(model, model_path)

    embedding, logits = run_onnx(model_path, np.zeros((2, 32_000), dtype=np.float32))
    assert embedding.shape == (2, 64)
    assert logits.shape == (2, 20)
    assert np.isfinite(embedding).all()
    assert np.isfinite(logits).all()


def test_mst005_calibration_reader_is_bounded_and_resettable() -> None:
    values = [np.full((1, 32_000), index, dtype=np.float32) for index in range(3)]
    reader = ArrayCalibrationReader(values)
    assert float(reader.get_next()["waveform"][0, 0]) == 0.0
    assert float(reader.get_next()["waveform"][0, 0]) == 1.0
    assert float(reader.get_next()["waveform"][0, 0]) == 2.0
    assert reader.get_next() is None
    reader.rewind()
    assert float(reader.get_next()["waveform"][0, 0]) == 0.0


def test_mst005_static_int8_preserves_student_outputs_on_speech_like_inputs(tmp_path: Path) -> None:
    torch.manual_seed(7)
    model = MobileWordStudent().eval()
    fp32_path = tmp_path / "student-fp32.onnx"
    int8_path = tmp_path / "student-int8.onnx"
    export_fp32_onnx(model, fp32_path)
    time = np.arange(32_000, dtype=np.float32) / 16_000.0
    waveforms = np.stack([
        (0.15 + index * 0.01) * np.sin(2 * np.pi * (120 + index * 17) * time)
        for index in range(20)
    ]).astype(np.float32)
    quantize_int8_onnx(fp32_path, int8_path, ArrayCalibrationReader([waveforms]))
    fp32_logits = run_onnx(fp32_path, waveforms)[1]
    int8_logits = run_onnx(int8_path, waveforms)[1]
    assert np.mean(fp32_logits.argmax(axis=1) == int8_logits.argmax(axis=1)) >= 0.99


def test_mst005_parity_accepts_literal_equal_outputs() -> None:
    logits = np.asarray([[4.0, 1.0], [0.0, 3.0], [5.0, -1.0], [-2.0, 2.0]])
    report = assess_quantization_parity(logits, logits.copy(), np.asarray([0, 1, 0, 1]))
    assert report.top1_agreement == 1.0
    assert report.probability_mae == 0.0
    assert report.macro_f1_loss == 0.0


def test_mst014_candidate_gate_rejects_subminimum_adult_int8_macro_f1() -> None:
    rejected = QuantizationParity(1.0, 1.0, 10, 1.0, 0.0, 0.299, 0.299, 0.0)
    accepted = QuantizationParity(1.0, 1.0, 10, 1.0, 0.0, 0.31, 0.30, 0.01)
    with pytest.raises(QuantizationGateError, match="adult_int8_macro_f1"):
        require_mobile_candidate_gate(rejected)
    require_mobile_candidate_gate(accepted)


def test_mst005_parity_abstains_from_low_margin_top1_flips() -> None:
    fp32 = np.vstack([np.asarray([[0.01, 0.0], [0.01, 0.0]]), np.tile([[4.0, 0.0]], (100, 1))])
    int8 = np.vstack([np.asarray([[0.0, 0.01], [0.0, 0.01]]), np.tile([[4.0, 0.0]], (100, 1))])
    report = assess_quantization_parity(fp32, int8, np.zeros(102, dtype=np.int64))
    assert report.top1_agreement == pytest.approx(100 / 102)
    assert report.actionable_top1_agreement == 1.0
    assert report.actionable_samples == 100


@pytest.mark.parametrize(
    ("fp32", "int8", "labels", "reason"),
    [
        (np.asarray([[4.0, 0.0], [4.0, 0.0]]), np.asarray([[0.0, 4.0], [4.0, 0.0]]), np.asarray([0, 0]), "top1_agreement"),
        (np.asarray([[4.0, 0.0]]), np.asarray([[0.5, 0.0]]), np.asarray([0]), "probability_mae"),
        (np.asarray([[4.0, 0.0], [0.0, 4.0]]), np.asarray([[4.0, 0.0], [4.0, 0.0]]), np.asarray([0, 1]), "top1_agreement"),
    ],
)
def test_mst005_parity_rejects_failed_acceptance_gate(
    fp32: np.ndarray, int8: np.ndarray, labels: np.ndarray, reason: str
) -> None:
    with pytest.raises(QuantizationGateError, match=reason):
        assess_quantization_parity(fp32, int8, labels)
