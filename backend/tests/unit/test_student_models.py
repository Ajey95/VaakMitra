from __future__ import annotations

import pytest
import torch
from modeling.distillation.students import CompactConformerCtc, CompactConvBiGruCtc


@pytest.mark.parametrize("model_kind", ["conformer", "conv_bigru"])
def test_students_return_dynamic_phoneme_logits_hidden_and_lengths(model_kind: str) -> None:
    if model_kind == "conformer":
        model = CompactConformerCtc(
            vocabulary_size=9,
            frontend_channels=8,
            hidden_size=16,
            encoder_layers=1,
            attention_heads=2,
        )
    else:
        model = CompactConvBiGruCtc(
            vocabulary_size=9,
            frontend_channels=8,
            hidden_size=12,
            encoder_layers=2,
        )
    audio = torch.zeros(2, 3_200)

    output = model(audio, torch.tensor([3_200, 2_400]))

    assert output.logits.shape[0] == 2
    assert output.logits.shape[2] == 9
    assert output.hidden.shape[:2] == output.logits.shape[:2]
    assert output.frame_lengths.shape == (2,)
    assert output.frame_lengths[0] > output.frame_lengths[1] > 0
    assert int(output.frame_lengths.max()) <= output.logits.shape[1]
    assert torch.isfinite(output.logits).all()


@pytest.mark.parametrize("model_kind", ["conformer", "conv_bigru"])
def test_students_report_nonempty_models_below_edge_size_ceiling(model_kind: str) -> None:
    model = (
        CompactConformerCtc(
            vocabulary_size=9,
            frontend_channels=8,
            hidden_size=16,
            encoder_layers=1,
            attention_heads=2,
        )
        if model_kind == "conformer"
        else CompactConvBiGruCtc(
            vocabulary_size=9,
            frontend_channels=8,
            hidden_size=12,
            encoder_layers=2,
        )
    )

    report = model.parameter_report()

    assert report.architecture == model_kind
    assert report.parameter_count == sum(parameter.numel() for parameter in model.parameters())
    assert 0 < report.fp32_size_bytes < 50_000_000


def test_student_rejects_nonfinite_audio_and_mismatched_lengths() -> None:
    model = CompactConvBiGruCtc(
        vocabulary_size=5,
        frontend_channels=8,
        hidden_size=8,
        encoder_layers=1,
    )
    audio = torch.zeros(1, 1_600)
    audio[0, 0] = torch.inf
    with pytest.raises(ValueError, match="finite"):
        model(audio, torch.tensor([1_600]))
    with pytest.raises(ValueError, match="input_lengths"):
        model(torch.zeros(2, 1_600), torch.tensor([1_600]))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"vocabulary_size": 1}, "vocabulary"),
        ({"hidden_size": 1024}, "hidden_size"),
        ({"encoder_layers": 0}, "encoder_layers"),
        ({"frontend_channels": 0}, "frontend_channels"),
    ],
)
def test_student_configuration_rejects_invalid_or_oversized_dimensions(
    kwargs: dict[str, int], message: str
) -> None:
    values = {
        "vocabulary_size": 8,
        "frontend_channels": 8,
        "hidden_size": 16,
        "encoder_layers": 1,
    }
    values.update(kwargs)
    with pytest.raises(ValueError, match=message):
        CompactConvBiGruCtc(**values)
