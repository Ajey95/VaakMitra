"""Phoneme-supervised hidden-representation distillation objectives."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from pydantic import BaseModel, ConfigDict, Field, model_validator
from torch import nn

from modeling.distillation.teacher_features import TeacherFeatureManifest
from modeling.training.phoneme_head import phoneme_ctc_loss


class DistillationWeights(BaseModel):
    """Allowed objectives; text-posterior KL is deliberately not part of this schema."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    supervised_ctc: float = Field(ge=0.0)
    representation: float = Field(ge=0.0)
    relational: float = Field(ge=0.0)
    sequence_consistency: float = Field(ge=0.0)

    @model_validator(mode="after")
    def require_positive_objective(self) -> DistillationWeights:
        if not any(
            value > 0
            for value in (
                self.supervised_ctc,
                self.representation,
                self.relational,
                self.sequence_consistency,
            )
        ):
            raise ValueError("at least one distillation weight must be positive")
        return self


@dataclass(frozen=True, slots=True)
class DistillationLosses:
    total: torch.Tensor
    supervised_ctc: torch.Tensor
    representation: torch.Tensor
    relational: torch.Tensor
    sequence_consistency: torch.Tensor


def _validate_hidden_pair(
    student: torch.Tensor, teacher: torch.Tensor, mask: torch.Tensor
) -> None:
    if student.ndim != 3 or teacher.shape != student.shape:
        raise ValueError("student and teacher representations must have the same shape")
    if mask.shape != student.shape[:2] or mask.dtype != torch.bool:
        raise ValueError("frame mask must be boolean [batch, frames]")
    if not torch.any(mask):
        raise ValueError("at least one valid frame is required")
    if not torch.isfinite(student).all() or not torch.isfinite(teacher).all():
        raise ValueError("representations must contain only finite values")


def masked_representation_loss(
    student: torch.Tensor, teacher: torch.Tensor, mask: torch.Tensor
) -> torch.Tensor:
    """Smooth-L1 hidden loss over valid frames only."""

    _validate_hidden_pair(student, teacher, mask)
    return nn.functional.smooth_l1_loss(student[mask], teacher[mask], reduction="mean")


def relational_frame_loss(
    student: torch.Tensor, teacher: torch.Tensor, mask: torch.Tensor
) -> torch.Tensor:
    """Preserve normalized pairwise frame similarities on valid frame pairs."""

    _validate_hidden_pair(student, teacher, mask)
    student_normalized = nn.functional.normalize(student, dim=-1)
    teacher_normalized = nn.functional.normalize(teacher, dim=-1)
    student_gram = student_normalized @ student_normalized.transpose(1, 2)
    teacher_gram = teacher_normalized @ teacher_normalized.transpose(1, 2)
    pair_mask = mask.unsqueeze(1) & mask.unsqueeze(2)
    return nn.functional.mse_loss(
        student_gram[pair_mask], teacher_gram[pair_mask], reduction="mean"
    )


def _sequence_consistency_loss(
    student: torch.Tensor, teacher: torch.Tensor, mask: torch.Tensor
) -> torch.Tensor:
    weights = mask.unsqueeze(-1).to(dtype=student.dtype)
    denominators = weights.sum(dim=1).clamp_min(1.0)
    student_pooled = (student * weights).sum(dim=1) / denominators
    teacher_pooled = (teacher * weights).sum(dim=1) / denominators
    similarity = nn.functional.cosine_similarity(student_pooled, teacher_pooled, dim=-1)
    return (1.0 - similarity).mean()


class DistillationCriterion(nn.Module):
    """Combine phoneme CTC with projected teacher representation objectives."""

    def __init__(
        self,
        *,
        student_dimension: int,
        teacher_dimension: int,
        weights: DistillationWeights,
        blank_index: int,
    ) -> None:
        super().__init__()
        if student_dimension <= 0 or teacher_dimension <= 0:
            raise ValueError("representation dimensions must be positive")
        if blank_index < 0:
            raise ValueError("blank_index must be non-negative")
        self.teacher_projection = nn.Linear(teacher_dimension, student_dimension, bias=False)
        self.weights = weights
        self.blank_index = blank_index

    def forward(
        self,
        *,
        logits: torch.Tensor,
        student_hidden: torch.Tensor,
        teacher_hidden: torch.Tensor,
        frame_lengths: torch.Tensor,
        padded_targets: torch.Tensor,
        target_lengths: torch.Tensor,
    ) -> DistillationLosses:
        if teacher_hidden.ndim != 3 or teacher_hidden.shape[:2] != student_hidden.shape[:2]:
            raise ValueError("teacher and student frame axes must match")
        projected_teacher = self.teacher_projection(teacher_hidden)
        positions = torch.arange(student_hidden.shape[1], device=frame_lengths.device).unsqueeze(0)
        mask = positions < frame_lengths.unsqueeze(1)
        supervised = phoneme_ctc_loss(
            logits,
            frame_lengths,
            padded_targets,
            target_lengths,
            blank_index=self.blank_index,
        )
        representation = masked_representation_loss(student_hidden, projected_teacher, mask)
        relational = relational_frame_loss(student_hidden, projected_teacher, mask)
        sequence = _sequence_consistency_loss(student_hidden, projected_teacher, mask)
        total = (
            self.weights.supervised_ctc * supervised
            + self.weights.representation * representation
            + self.weights.relational * relational
            + self.weights.sequence_consistency * sequence
        )
        if not torch.isfinite(total):
            raise FloatingPointError("non-finite distillation loss")
        return DistillationLosses(
            total=total,
            supervised_ctc=supervised,
            representation=representation,
            relational=relational,
            sequence_consistency=sequence,
        )


def validate_teacher_cache_binding(
    manifest: TeacherFeatureManifest,
    *,
    expected_revision: str,
    expected_audio_sha256: str,
) -> None:
    """Reject a cached tensor unless its teacher and audio digests match the batch."""

    if manifest.model_revision != expected_revision:
        raise ValueError("teacher cache model revision mismatch")
    if manifest.audio_sha256 != expected_audio_sha256:
        raise ValueError("teacher cache audio digest mismatch")
