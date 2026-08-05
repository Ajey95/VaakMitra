from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxruntime as ort
import pytest
import torch
from modeling.distillation.students import CompactConformerCtc, CompactConvBiGruCtc
from modeling.export.export_onnx import export_student_onnx
from modeling.quantization.quantize_onnx import quantize_dynamic_int8
from modeling.validation.model_parity import compare_model_parity


@pytest.mark.parametrize("architecture", ["conformer", "conv_bigru"])
def test_student_fixture_exports_dynamic_onnx_and_runs_int8(
    tmp_path: Path, architecture: str
) -> None:
    torch.manual_seed(5)
    model = (
        CompactConformerCtc(
            vocabulary_size=4,
            frontend_channels=4,
            hidden_size=8,
            encoder_layers=1,
            attention_heads=2,
        )
        if architecture == "conformer"
        else CompactConvBiGruCtc(
            vocabulary_size=4,
            frontend_channels=4,
            hidden_size=4,
            encoder_layers=1,
        )
    )
    fp32_path = tmp_path / f"{architecture}-fp32.onnx"
    int8_path = tmp_path / f"{architecture}-int8.onnx"

    metadata = export_student_onnx(
        model,
        fp32_path,
        example_samples=1_600,
        config_sha256="a" * 64,
        vocabulary_sha256="b" * 64,
    )
    quantize_dynamic_int8(fp32_path, int8_path)

    audio = np.zeros((1, 1_600), dtype=np.float32)
    lengths = np.array([1_600], dtype=np.int64)
    fp32_outputs = ort.InferenceSession(
        str(fp32_path), providers=["CPUExecutionProvider"]
    ).run(None, {"audio": audio, "input_lengths": lengths})
    int8_outputs = ort.InferenceSession(
        str(int8_path), providers=["CPUExecutionProvider"]
    ).run(None, {"audio": audio, "input_lengths": lengths})
    with torch.no_grad():
        torch_logits = model(torch.from_numpy(audio), torch.from_numpy(lengths)).logits.numpy()
    parity = compare_model_parity(
        torch_logits,
        fp32_outputs[0],
        blank_index=0,
        reference_per=0.0,
        candidate_per=0.0,
        reference_gop=(),
        candidate_gop=(),
    )

    assert metadata.artifact.sha256
    assert metadata.config_sha256 == "a" * 64
    assert metadata.vocabulary_sha256 == "b" * 64
    assert metadata.output_kind == "phoneme_logits"
    assert metadata.dynamic_sample_axis is True
    assert parity.max_absolute_logit_delta < 1e-4
    assert int8_outputs[0].shape == fp32_outputs[0].shape
    assert int8_outputs[1].tolist() == fp32_outputs[1].tolist()
