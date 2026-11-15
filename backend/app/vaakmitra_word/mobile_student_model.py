"""Compact raw-waveform network for the DEC-028/029 Android review bundle."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as functional


class DepthwiseSeparableBlock(nn.Module):
    def __init__(self, input_channels: int, output_channels: int, *, stride: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv1d(
                input_channels,
                input_channels,
                kernel_size=9,
                stride=stride,
                padding=4,
                groups=input_channels,
                bias=False,
            ),
            nn.BatchNorm1d(input_channels),
            nn.ReLU6(inplace=False),
            nn.Conv1d(input_channels, output_channels, kernel_size=1, bias=False),
            nn.BatchNorm1d(output_channels),
            nn.ReLU6(inplace=False),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.layers(values)


class FixedTemporalRegionPool(nn.Module):
    """MST-012 ordered pooling with deterministic CUDA gradients for 32k input."""

    output_size = 8
    _bounds = ((0, 2), (2, 4), (4, 6), (6, 7), (7, 9), (9, 10), (10, 12), (12, 13))

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return torch.cat(
            [values[:, :, start:end].mean(dim=2, keepdim=True) for start, end in self._bounds],
            dim=2,
        )


class MobileWordStudent(nn.Module):
    """MST-004/011/012 model: normalized 32k waveform -> embedding and logits."""

    def __init__(self, *, classes: int = 20, embedding_dimensions: int = 64) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=400, stride=160, padding=120, bias=False),
            nn.BatchNorm1d(32),
            nn.ReLU6(inplace=False),
            DepthwiseSeparableBlock(32, 48, stride=2),
            DepthwiseSeparableBlock(48, 64, stride=2),
            DepthwiseSeparableBlock(64, 80, stride=2),
            DepthwiseSeparableBlock(80, 96, stride=2),
        )
        self.temporal_pool = FixedTemporalRegionPool()
        self.embedding = nn.Linear(96 * 8, embedding_dimensions)
        self.classifier = nn.Linear(embedding_dimensions, classes)

    def forward(self, waveform: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if waveform.ndim == 2:
            waveform = waveform.unsqueeze(1)
        # MST-011: graph-owned normalization makes desktop and Android use the
        # identical channel correction and keeps silence numerically finite.
        waveform = waveform - waveform.mean(dim=2, keepdim=True)
        rms = torch.sqrt(torch.mean(waveform * waveform, dim=2, keepdim=True) + 1e-8)
        waveform = torch.clamp((waveform / torch.clamp(rms, min=1e-4)) * 0.08, min=-0.95, max=0.95)
        encoded = self.encoder(waveform)
        # MST-012: retain eight ordered regions rather than erasing word order.
        pooled = self.temporal_pool(encoded).flatten(start_dim=1)
        embedding = functional.normalize(self.embedding(pooled), p=2.0, dim=1, eps=1e-8)
        return embedding, self.classifier(embedding)


def student_loss(
    logits: torch.Tensor,
    hard_labels: torch.Tensor,
    teacher_probabilities: torch.Tensor | None,
    *,
    temperature: float = 2.0,
) -> torch.Tensor:
    """MST-004 supervised loss with optional frozen-teacher distillation."""
    hard_loss = functional.cross_entropy(logits, hard_labels)
    if teacher_probabilities is None:
        return hard_loss
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    teacher = teacher_probabilities.to(device=logits.device, dtype=logits.dtype)
    teacher = teacher / teacher.sum(dim=1, keepdim=True).clamp_min(1e-12)
    soft_loss = functional.kl_div(
        functional.log_softmax(logits / temperature, dim=1),
        teacher,
        reduction="batchmean",
    ) * (temperature * temperature)
    return 0.6 * hard_loss + 0.4 * soft_loss
