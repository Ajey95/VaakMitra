"""Compact phoneme CTC students for teacher distillation and edge export."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass(frozen=True, slots=True)
class StudentOutput:
    logits: torch.Tensor
    hidden: torch.Tensor
    frame_lengths: torch.Tensor


@dataclass(frozen=True, slots=True)
class ParameterReport:
    architecture: str
    parameter_count: int
    fp32_size_bytes: int


def _validate_dimensions(
    *,
    vocabulary_size: int,
    frontend_channels: int,
    hidden_size: int,
    encoder_layers: int,
) -> None:
    if vocabulary_size <= 1:
        raise ValueError("vocabulary_size must include blank and nonblank tokens")
    if frontend_channels <= 0 or frontend_channels > 256:
        raise ValueError("frontend_channels must be between 1 and 256")
    if hidden_size <= 0 or hidden_size > 512:
        raise ValueError("hidden_size must be between 1 and 512")
    if encoder_layers <= 0 or encoder_layers > 8:
        raise ValueError("encoder_layers must be between 1 and 8")


def _validate_audio(
    audio: torch.Tensor, input_lengths: torch.Tensor, *, minimum_samples: int
) -> None:
    if audio.ndim != 2 or audio.shape[0] == 0 or audio.shape[1] < minimum_samples:
        raise ValueError(f"audio must be [batch, samples] with at least {minimum_samples} samples")
    if not torch.isfinite(audio).all():
        raise ValueError("audio must contain only finite values")
    if input_lengths.shape != (audio.shape[0],):
        raise ValueError("input_lengths must contain one value per batch item")
    if torch.any(input_lengths < minimum_samples) or torch.any(
        input_lengths > audio.shape[1]
    ):
        raise ValueError("input_lengths must be within the audio sample dimension")


def _length_mask(frame_lengths: torch.Tensor, frame_count: int) -> torch.Tensor:
    positions = torch.arange(frame_count, device=frame_lengths.device).unsqueeze(0)
    return positions < frame_lengths.unsqueeze(1)


class _WaveFrontend(nn.Module):
    minimum_samples = 400

    def __init__(self, channels: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv1d(1, channels, kernel_size=400, stride=160),
            nn.GELU(),
            nn.Conv1d(channels, channels, kernel_size=5, stride=2, padding=2),
            nn.GELU(),
        )

    @staticmethod
    def output_lengths(input_lengths: torch.Tensor) -> torch.Tensor:
        first = torch.div(input_lengths - 400, 160, rounding_mode="floor") + 1
        second = torch.div(first + 1, 2, rounding_mode="floor")
        return second.clamp_min(0).to(dtype=torch.long)

    def forward(self, audio: torch.Tensor) -> torch.Tensor:
        return self.layers(audio.unsqueeze(1)).transpose(1, 2)


class _StudentBase(nn.Module):
    architecture: str

    def parameter_report(self) -> ParameterReport:
        count = sum(parameter.numel() for parameter in self.parameters())
        return ParameterReport(
            architecture=self.architecture,
            parameter_count=count,
            fp32_size_bytes=count * 4,
        )


class CompactConformerCtc(_StudentBase):
    """Small self-attentive acoustic encoder used as the primary student candidate."""

    architecture = "conformer"

    def __init__(
        self,
        *,
        vocabulary_size: int,
        frontend_channels: int = 48,
        hidden_size: int = 128,
        encoder_layers: int = 4,
        attention_heads: int = 4,
    ) -> None:
        super().__init__()
        _validate_dimensions(
            vocabulary_size=vocabulary_size,
            frontend_channels=frontend_channels,
            hidden_size=hidden_size,
            encoder_layers=encoder_layers,
        )
        if attention_heads <= 0 or hidden_size % attention_heads != 0:
            raise ValueError("attention_heads must divide hidden_size")
        self.frontend = _WaveFrontend(frontend_channels)
        self.input_projection = nn.Linear(frontend_channels, hidden_size)
        layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=attention_heads,
            dim_feedforward=hidden_size * 4,
            dropout=0.0,
            activation="gelu",
            batch_first=True,
            norm_first=False,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=encoder_layers)
        self.ctc_head = nn.Linear(hidden_size, vocabulary_size)

    def forward(self, audio: torch.Tensor, input_lengths: torch.Tensor) -> StudentOutput:
        _validate_audio(
            audio, input_lengths, minimum_samples=self.frontend.minimum_samples
        )
        frame_lengths = self.frontend.output_lengths(input_lengths)
        features = self.input_projection(self.frontend(audio))
        valid_mask = _length_mask(frame_lengths, features.shape[1])
        hidden = self.encoder(features, src_key_padding_mask=~valid_mask)
        hidden = hidden.masked_fill(~valid_mask.unsqueeze(-1), 0.0)
        logits = self.ctc_head(hidden)
        if not torch.isfinite(logits).all():
            raise FloatingPointError("student logits are non-finite")
        return StudentOutput(logits=logits, hidden=hidden, frame_lengths=frame_lengths)


class CompactConvBiGruCtc(_StudentBase):
    """Improved convolutional BiGRU baseline under the same phoneme contract."""

    architecture = "conv_bigru"

    def __init__(
        self,
        *,
        vocabulary_size: int,
        frontend_channels: int = 48,
        hidden_size: int = 96,
        encoder_layers: int = 2,
    ) -> None:
        super().__init__()
        _validate_dimensions(
            vocabulary_size=vocabulary_size,
            frontend_channels=frontend_channels,
            hidden_size=hidden_size,
            encoder_layers=encoder_layers,
        )
        self.frontend = _WaveFrontend(frontend_channels)
        self.encoder = nn.GRU(
            input_size=frontend_channels,
            hidden_size=hidden_size,
            num_layers=encoder_layers,
            batch_first=True,
            bidirectional=True,
            dropout=0.0,
        )
        self.ctc_head = nn.Linear(hidden_size * 2, vocabulary_size)

    def forward(self, audio: torch.Tensor, input_lengths: torch.Tensor) -> StudentOutput:
        _validate_audio(
            audio, input_lengths, minimum_samples=self.frontend.minimum_samples
        )
        frame_lengths = self.frontend.output_lengths(input_lengths)
        features = self.frontend(audio)
        hidden, _ = self.encoder(features)
        valid_mask = _length_mask(frame_lengths, hidden.shape[1])
        hidden = hidden.masked_fill(~valid_mask.unsqueeze(-1), 0.0)
        logits = self.ctc_head(hidden)
        if not torch.isfinite(logits).all():
            raise FloatingPointError("student logits are non-finite")
        return StudentOutput(logits=logits, hidden=hidden, frame_lengths=frame_lengths)
