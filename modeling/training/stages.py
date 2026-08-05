"""Deterministic staged-unfreezing policy for a phoneme-headed teacher encoder."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import cast

from torch import nn


class TrainingStage(str, Enum):
    HEAD_ONLY = "head_only"
    TOP_ENCODER_BLOCKS = "top_encoder_blocks"
    FULL_ENCODER = "full_encoder"


@dataclass(frozen=True, slots=True)
class FreezeReport:
    stage: TrainingStage
    trainable_groups: tuple[str, ...]
    trainable_parameter_count: int
    total_parameter_count: int


def _set_requires_grad(module: nn.Module, enabled: bool) -> None:
    for parameter in module.parameters():
        parameter.requires_grad = enabled


def select_trainable_parameters(
    model: nn.Module,
    stage: TrainingStage,
    *,
    top_block_count: int = 2,
) -> FreezeReport:
    """Apply one auditable freeze schedule to `encoder` and `phoneme_head`."""

    encoder = cast(nn.Module, getattr(model, "encoder", None))
    phoneme_head = cast(nn.Module, getattr(model, "phoneme_head", None))
    if not isinstance(encoder, nn.Module) or not isinstance(phoneme_head, nn.Module):
        raise TypeError("model must expose encoder and phoneme_head modules")
    _set_requires_grad(model, False)

    groups: list[str] = []
    if stage == TrainingStage.HEAD_ONLY:
        _set_requires_grad(phoneme_head, True)
        groups.append("phoneme_head")
    elif stage == TrainingStage.TOP_ENCODER_BLOCKS:
        layers = cast(nn.ModuleList, getattr(encoder, "layers", None))
        if not isinstance(layers, nn.ModuleList):
            raise TypeError("top-block training requires encoder.layers ModuleList")
        if top_block_count <= 0 or top_block_count > len(layers):
            raise ValueError("top_block_count must select existing trailing blocks")
        start = len(layers) - top_block_count
        for index in range(start, len(layers)):
            _set_requires_grad(layers[index], True)
            groups.append(f"encoder.layers.{index}")
        _set_requires_grad(phoneme_head, True)
        groups.append("phoneme_head")
    elif stage == TrainingStage.FULL_ENCODER:
        _set_requires_grad(model, True)
        groups.extend(("encoder", "phoneme_head"))
    else:
        raise ValueError("unsupported training stage")

    total = sum(parameter.numel() for parameter in model.parameters())
    trainable = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    return FreezeReport(
        stage=stage,
        trainable_groups=tuple(groups),
        trainable_parameter_count=trainable,
        total_parameter_count=total,
    )


def next_training_stage(
    current: TrainingStage,
    *,
    before_per: float,
    after_per: float,
    minimum_improvement: float,
) -> TrainingStage:
    """Advance only after a finite, predeclared validation PER improvement."""

    if any(not math.isfinite(value) or value < 0 for value in (before_per, after_per)):
        raise ValueError("phone error rates must be finite and non-negative")
    if not math.isfinite(minimum_improvement) or minimum_improvement < 0:
        raise ValueError("minimum_improvement must be finite and non-negative")
    improvement = before_per - after_per
    if current == TrainingStage.HEAD_ONLY and improvement >= minimum_improvement:
        return TrainingStage.TOP_ENCODER_BLOCKS
    if current == TrainingStage.TOP_ENCODER_BLOCKS and improvement >= minimum_improvement:
        return TrainingStage.FULL_ENCODER
    return current
