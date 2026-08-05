from __future__ import annotations

import pytest
import torch
from modeling.training.ctc_batch import PhonemeBatch
from modeling.training.phoneme_head import PhonemeCtcModel, phoneme_ctc_loss
from modeling.training.stages import TrainingStage, select_trainable_parameters
from torch import nn


class FixtureEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layers = nn.ModuleList([nn.Linear(4, 4)])
        self.output_size = 4

    def forward(
        self, audio: torch.Tensor, input_lengths: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        frames = audio[:, :16].reshape(audio.shape[0], 4, 4)
        return self.layers[0](frames), torch.div(input_lengths, 4, rounding_mode="floor")


def test_phoneme_head_outputs_vocab_logits_and_propagates_lengths() -> None:
    model = PhonemeCtcModel(FixtureEncoder(), hidden_size=4, vocabulary_size=5)

    logits, lengths = model(torch.zeros(2, 16), torch.tensor([16, 12]))

    assert logits.shape == (2, 4, 5)
    assert lengths.tolist() == [4, 3]
    assert model.blank_index == 0


def test_ctc_loss_is_finite_and_head_only_stage_blocks_encoder_gradients() -> None:
    model = PhonemeCtcModel(FixtureEncoder(), hidden_size=4, vocabulary_size=4)
    select_trainable_parameters(model, TrainingStage.HEAD_ONLY)
    logits, lengths = model(torch.zeros(1, 16), torch.tensor([16]))

    loss = phoneme_ctc_loss(
        logits,
        lengths,
        torch.tensor([[1, 2, -1]]),
        torch.tensor([2]),
        blank_index=0,
    )
    loss.backward()

    assert torch.isfinite(loss)
    assert not any(parameter.grad is not None for parameter in model.encoder.parameters())
    assert all(parameter.grad is not None for parameter in model.phoneme_head.parameters())


def test_ctc_loss_rejects_blank_targets_and_impossible_lengths() -> None:
    logits = torch.zeros(1, 2, 3)
    with pytest.raises(ValueError, match="blank"):
        phoneme_ctc_loss(
            logits,
            torch.tensor([2]),
            torch.tensor([[0]]),
            torch.tensor([1]),
            blank_index=0,
        )
    with pytest.raises(ValueError, match="target length"):
        phoneme_ctc_loss(
            logits,
            torch.tensor([1]),
            torch.tensor([[1, 2]]),
            torch.tensor([2]),
            blank_index=0,
        )


def test_model_rejects_nonfinite_audio_and_encoder_outputs() -> None:
    model = PhonemeCtcModel(FixtureEncoder(), hidden_size=4, vocabulary_size=3)
    audio = torch.zeros(1, 16)
    audio[0, 0] = torch.nan

    with pytest.raises(ValueError, match="finite"):
        model(audio, torch.tensor([16]))


def test_phoneme_batch_validates_lengths_and_padding_without_storing_text() -> None:
    batch = PhonemeBatch(
        audio=torch.zeros(2, 16),
        input_lengths=torch.tensor([16, 12]),
        padded_targets=torch.tensor([[1, 2, -1], [2, -1, -1]]),
        target_lengths=torch.tensor([2, 1]),
    )

    batch.validate(vocabulary_size=4, blank_index=0)
    with pytest.raises(ValueError, match="padding"):
        PhonemeBatch(
            audio=torch.zeros(1, 16),
            input_lengths=torch.tensor([16]),
            padded_targets=torch.tensor([[1, 2]]),
            target_lengths=torch.tensor([1]),
        ).validate(vocabulary_size=4, blank_index=0)


@pytest.mark.parametrize(
    ("hidden_size", "vocabulary_size"),
    [(0, 3), (4, 1)],
)
def test_model_rejects_invalid_dimensions(hidden_size: int, vocabulary_size: int) -> None:
    with pytest.raises(ValueError, match=r"dimension|vocabulary"):
        PhonemeCtcModel(
            FixtureEncoder(), hidden_size=hidden_size, vocabulary_size=vocabulary_size
        )
