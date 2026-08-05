from __future__ import annotations

import pytest
from modeling.training.stages import (
    TrainingStage,
    next_training_stage,
    select_trainable_parameters,
)
from torch import nn


class FixtureModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Module()
        self.encoder.layers = nn.ModuleList([nn.Linear(4, 4) for _ in range(4)])
        self.phoneme_head = nn.Linear(4, 3)


def test_head_stage_freezes_everything_except_phoneme_head() -> None:
    model = FixtureModel()

    report = select_trainable_parameters(model, TrainingStage.HEAD_ONLY)

    assert report.trainable_groups == ("phoneme_head",)
    assert all(parameter.requires_grad for parameter in model.phoneme_head.parameters())
    assert not any(parameter.requires_grad for parameter in model.encoder.parameters())


def test_top_encoder_stage_unfreezes_only_requested_trailing_blocks() -> None:
    model = FixtureModel()

    report = select_trainable_parameters(
        model, TrainingStage.TOP_ENCODER_BLOCKS, top_block_count=2
    )

    assert report.trainable_groups == ("encoder.layers.2", "encoder.layers.3", "phoneme_head")
    assert not any(parameter.requires_grad for parameter in model.encoder.layers[0].parameters())
    assert all(parameter.requires_grad for parameter in model.encoder.layers[3].parameters())


def test_full_encoder_stage_unfreezes_all_parameters() -> None:
    model = FixtureModel()

    report = select_trainable_parameters(model, TrainingStage.FULL_ENCODER)

    assert report.trainable_parameter_count == report.total_parameter_count
    assert all(parameter.requires_grad for parameter in model.parameters())


def test_full_encoder_is_selected_only_after_validation_improvement() -> None:
    assert (
        next_training_stage(
            TrainingStage.TOP_ENCODER_BLOCKS,
            before_per=0.40,
            after_per=0.35,
            minimum_improvement=0.01,
        )
        == TrainingStage.FULL_ENCODER
    )
    assert (
        next_training_stage(
            TrainingStage.TOP_ENCODER_BLOCKS,
            before_per=0.40,
            after_per=0.395,
            minimum_improvement=0.01,
        )
        == TrainingStage.TOP_ENCODER_BLOCKS
    )


@pytest.mark.parametrize("top_block_count", [0, -1, 5])
def test_top_encoder_stage_rejects_invalid_block_counts(top_block_count: int) -> None:
    with pytest.raises(ValueError, match="top_block_count"):
        select_trainable_parameters(
            FixtureModel(),
            TrainingStage.TOP_ENCODER_BLOCKS,
            top_block_count=top_block_count,
        )
