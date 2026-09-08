from __future__ import annotations

from pathlib import Path

import numpy as np
import onnxruntime as ort
import pytest
import torch
from modeling.distillation.students import CompactConformerCtc, CompactConvBiGruCtc
from modeling.export.export_onnx import export_student_onnx
from modeling.export.reference_artifact import export_reference_candidate
from modeling.quantization.quantize_onnx import quantize_dynamic_int8
from modeling.validation.model_parity import compare_model_parity
from torch import nn


class _ReferenceFixture(nn.Module):
    def forward(
        self,
        audio: torch.Tensor,
        input_lengths: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        frames = audio[:, ::4]
        logits = torch.stack((torch.zeros_like(frames), frames, -frames), dim=-1)
        frame_lengths = torch.div(input_lengths + 3, 4, rounding_mode="floor")
        return logits, frame_lengths


def test_reference_candidate_exports_dynamic_onnx_with_pytorch_parity(
    tmp_path: Path,
) -> None:
    model = _ReferenceFixture().eval()
    checkpoint = tmp_path / "selected.pt"
    checkpoint.write_bytes(b"native checkpoint")
    validation = tmp_path / "validation.json"
    validation.write_text('{"phoneme_error_rate":0.4}\n', encoding="utf-8")
    result = export_reference_candidate(
        model=model,
        native_checkpoint=checkpoint,
        output_dir=tmp_path / "reference",
        tokens=("<blank>", "a", "b"),
        run_binding={"binding_sha256": "c" * 64},
        artifact_role="head_only_candidate",
        selected_stage="head_only",
        validation_metrics_path=validation,
        test_metrics_path=None,
        sample_rate_hz=16_000,
        frame_subsampling=4,
    )

    assert result.onnx_status == "passed"
    assert result.onnx_path is not None
    session = ort.InferenceSession(str(result.onnx_path), providers=["CPUExecutionProvider"])
    for sample_count in (16_000, 32_000):
        audio = np.linspace(-0.5, 0.5, sample_count, dtype=np.float32)[None, :]
        lengths = np.array([sample_count], dtype=np.int64)
        onnx_logits, onnx_lengths = session.run(
            None,
            {"audio": audio, "input_lengths": lengths},
        )
        with torch.inference_mode():
            torch_logits, torch_lengths = model(
                torch.from_numpy(audio),
                torch.from_numpy(lengths),
            )
        assert onnx_logits.shape == tuple(torch_logits.shape)
        assert onnx_lengths.tolist() == torch_lengths.tolist()
        assert np.isfinite(onnx_logits).all()
        assert np.max(np.abs(onnx_logits - torch_logits.numpy())) < 1e-6


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
