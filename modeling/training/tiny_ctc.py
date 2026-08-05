"""Small raw-waveform CTC network for a labelled adult-Tamil proxy experiment."""

from __future__ import annotations

import collections
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import torch
from torch import nn

from modeling.training.proxy_dataset import proxy_phone_units


@dataclass(frozen=True, slots=True)
class ProxyPhoneVocabulary:
    tokens: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.tokens) < 3 or self.tokens[:2] != ("<blank>", "<unk>"):
            raise ValueError("proxy vocabulary must start with blank and unknown tokens")
        if len(self.tokens) != len(set(self.tokens)):
            raise ValueError("proxy vocabulary tokens must be unique")

    @property
    def blank_index(self) -> int:
        return 0

    def encode(self, phoneme_text: str) -> tuple[int, ...]:
        indices = {token: index for index, token in enumerate(self.tokens)}
        return tuple(indices.get(unit, 1) for unit in proxy_phone_units(phoneme_text))


def build_proxy_vocabulary(
    phoneme_sequences: Sequence[str],
    *,
    minimum_frequency: int = 1,
) -> ProxyPhoneVocabulary:
    if minimum_frequency <= 0:
        raise ValueError("minimum_frequency must be positive")
    counts = collections.Counter(
        unit for sequence in phoneme_sequences for unit in proxy_phone_units(sequence)
    )
    units = tuple(sorted(unit for unit, count in counts.items() if count >= minimum_frequency))
    if not units:
        raise ValueError("proxy vocabulary requires at least one observed unit")
    return ProxyPhoneVocabulary(("<blank>", "<unk>", *units))


class TinyWaveCtc(nn.Module):
    """Direct waveform-to-CTC logits model with an approximately 20 ms frame step."""

    def __init__(self, vocabulary_size: int, *, channels: int = 48, hidden_size: int = 64) -> None:
        super().__init__()
        if vocabulary_size <= 2 or channels <= 0 or hidden_size <= 0:
            raise ValueError("model dimensions must be positive and vocabulary_size must exceed two")
        self.frontend = nn.Sequential(
            nn.Conv1d(1, channels, kernel_size=400, stride=160),
            nn.GELU(),
            nn.Conv1d(channels, channels, kernel_size=5, stride=2, padding=2),
            nn.GELU(),
            nn.Conv1d(channels, channels, kernel_size=3, padding=1),
            nn.GELU(),
        )
        self.encoder = nn.GRU(
            input_size=channels,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
            bidirectional=True,
        )
        self.ctc_head = nn.Linear(hidden_size * 2, vocabulary_size)

    @staticmethod
    def output_lengths(input_lengths: torch.Tensor) -> torch.Tensor:
        first = torch.div(input_lengths - 400, 160, rounding_mode="floor") + 1
        return torch.div(first + 1, 2, rounding_mode="floor").clamp_min(0)

    def forward(self, audio: torch.Tensor) -> torch.Tensor:
        if audio.ndim != 2 or audio.shape[1] < 400:
            raise ValueError("audio must have shape [batch, samples] with at least 400 samples")
        features = self.frontend(audio.unsqueeze(1)).transpose(1, 2)
        encoded, _ = self.encoder(features)
        return cast(torch.Tensor, self.ctc_head(encoded))
