"""Strict in-memory batch validation for phoneme CTC training."""

from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True, slots=True)
class PhonemeBatch:
    audio: torch.Tensor
    input_lengths: torch.Tensor
    padded_targets: torch.Tensor
    target_lengths: torch.Tensor

    def validate(self, *, vocabulary_size: int, blank_index: int) -> None:
        if vocabulary_size <= 1 or not 0 <= blank_index < vocabulary_size:
            raise ValueError("invalid vocabulary size or blank index")
        if self.audio.ndim != 2 or self.audio.shape[0] == 0 or self.audio.shape[1] == 0:
            raise ValueError("audio must be non-empty [batch, samples]")
        if not torch.isfinite(self.audio).all():
            raise ValueError("audio must contain only finite values")
        batch_size = self.audio.shape[0]
        if self.input_lengths.shape != (batch_size,):
            raise ValueError("input_lengths must contain one value per batch item")
        if torch.any(self.input_lengths <= 0) or torch.any(
            self.input_lengths > self.audio.shape[1]
        ):
            raise ValueError("input_lengths must be within the audio sample dimension")
        if self.padded_targets.ndim != 2 or self.padded_targets.shape[0] != batch_size:
            raise ValueError("padded_targets must be [batch, target_steps]")
        if self.target_lengths.shape != (batch_size,):
            raise ValueError("target_lengths must contain one value per batch item")
        if torch.any(self.target_lengths <= 0) or torch.any(
            self.target_lengths > self.padded_targets.shape[1]
        ):
            raise ValueError("target_lengths must select non-empty target sequences")
        for targets, raw_length in zip(
            self.padded_targets, self.target_lengths.tolist(), strict=True
        ):
            length = int(raw_length)
            selected = targets[:length]
            padding = targets[length:]
            if torch.any(selected < 0) or torch.any(selected >= vocabulary_size):
                raise ValueError("target index is outside the vocabulary")
            if torch.any(selected == blank_index):
                raise ValueError("target sequence cannot contain the CTC blank")
            if torch.any(padding != -1):
                raise ValueError("target padding must use -1 outside target_lengths")
