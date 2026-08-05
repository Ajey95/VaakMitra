"""Reusable phoneme CTC head for an IndicConformer-compatible acoustic encoder."""

from __future__ import annotations

from typing import Protocol

import torch
from torch import nn


class AcousticEncoder(Protocol):
    def __call__(
        self, audio: torch.Tensor, input_lengths: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]: ...


class PhonemeCtcModel(nn.Module):
    """Attach a new phoneme projection without reusing upstream text logits."""

    blank_index = 0

    def __init__(
        self,
        encoder: nn.Module,
        *,
        hidden_size: int,
        vocabulary_size: int,
    ) -> None:
        super().__init__()
        if hidden_size <= 0:
            raise ValueError("hidden dimension must be positive")
        if vocabulary_size <= 1:
            raise ValueError("phoneme vocabulary must include blank and nonblank tokens")
        self.encoder = encoder
        self.phoneme_head = nn.Linear(hidden_size, vocabulary_size)

    def forward(
        self, audio: torch.Tensor, input_lengths: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if audio.ndim != 2 or audio.shape[0] == 0 or audio.shape[1] == 0:
            raise ValueError("audio must be non-empty [batch, samples]")
        if not torch.isfinite(audio).all():
            raise ValueError("audio must contain only finite values")
        if input_lengths.ndim != 1 or input_lengths.shape[0] != audio.shape[0]:
            raise ValueError("input_lengths must contain one value per batch item")
        if torch.any(input_lengths <= 0) or torch.any(input_lengths > audio.shape[1]):
            raise ValueError("input_lengths must be positive and within the sample dimension")

        encoded, frame_lengths = self.encoder(audio, input_lengths)
        if encoded.ndim != 3 or encoded.shape[0] != audio.shape[0]:
            raise ValueError("encoder output must be [batch, frames, hidden]")
        if not torch.isfinite(encoded).all():
            raise ValueError("encoder output must contain only finite values")
        if frame_lengths.ndim != 1 or frame_lengths.shape[0] != audio.shape[0]:
            raise ValueError("encoder frame lengths must contain one value per batch item")
        if torch.any(frame_lengths <= 0) or torch.any(frame_lengths > encoded.shape[1]):
            raise ValueError("encoder frame lengths must be positive and within the frame axis")
        logits = self.phoneme_head(encoded)
        if not torch.isfinite(logits).all():
            raise ValueError("phoneme logits must contain only finite values")
        return logits, frame_lengths.to(dtype=torch.long)


def phoneme_ctc_loss(
    logits: torch.Tensor,
    frame_lengths: torch.Tensor,
    padded_targets: torch.Tensor,
    target_lengths: torch.Tensor,
    *,
    blank_index: int,
) -> torch.Tensor:
    """Validate and compute finite batch-mean CTC loss from padded phoneme targets."""

    if logits.ndim != 3 or logits.shape[0] == 0 or logits.shape[2] <= 1:
        raise ValueError("logits must be non-empty [batch, frames, vocabulary]")
    if not torch.isfinite(logits).all():
        raise ValueError("logits must contain only finite values")
    batch_size, frame_count, vocabulary_size = logits.shape
    if not 0 <= blank_index < vocabulary_size:
        raise ValueError("blank index must exist in the vocabulary")
    if frame_lengths.shape != (batch_size,) or target_lengths.shape != (batch_size,):
        raise ValueError("length tensors must contain one value per batch item")
    if padded_targets.ndim != 2 or padded_targets.shape[0] != batch_size:
        raise ValueError("padded_targets must be [batch, target_steps]")
    if torch.any(frame_lengths <= 0) or torch.any(frame_lengths > frame_count):
        raise ValueError("frame lengths must be positive and within logits")
    if torch.any(target_lengths < 0) or torch.any(target_lengths > padded_targets.shape[1]):
        raise ValueError("target lengths must be within padded_targets")
    if torch.any(target_lengths > frame_lengths):
        raise ValueError("target length cannot exceed available CTC frames")

    flattened: list[torch.Tensor] = []
    for row, length in zip(padded_targets, target_lengths.tolist(), strict=True):
        selected = row[: int(length)].to(dtype=torch.long)
        if torch.any(selected == blank_index):
            raise ValueError("phoneme targets cannot contain the CTC blank")
        if torch.any(selected < 0) or torch.any(selected >= vocabulary_size):
            raise ValueError("phoneme target index is outside the vocabulary")
        flattened.append(selected)
    targets = torch.cat(flattened) if flattened else torch.empty(0, dtype=torch.long)
    loss = nn.functional.ctc_loss(
        logits.log_softmax(dim=-1).transpose(0, 1),
        targets,
        frame_lengths.to(dtype=torch.long),
        target_lengths.to(dtype=torch.long),
        blank=blank_index,
        reduction="mean",
        zero_infinity=True,
    )
    if not torch.isfinite(loss):
        raise FloatingPointError("non-finite phoneme CTC loss")
    return loss
