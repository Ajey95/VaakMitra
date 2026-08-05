"""One finite-gradient student optimization step shared by both candidates."""

from __future__ import annotations

import torch
from torch import nn

from modeling.distillation.losses import DistillationCriterion, DistillationLosses
from modeling.distillation.students import StudentOutput
from modeling.training.ctc_batch import PhonemeBatch


def distillation_training_step(
    *,
    model: nn.Module,
    criterion: DistillationCriterion,
    optimizer: torch.optim.Optimizer,
    batch: PhonemeBatch,
    teacher_hidden: torch.Tensor,
    vocabulary_size: int,
    gradient_clip_norm: float,
) -> DistillationLosses:
    if gradient_clip_norm <= 0:
        raise ValueError("gradient_clip_norm must be positive")
    batch.validate(vocabulary_size=vocabulary_size, blank_index=criterion.blank_index)
    optimizer.zero_grad(set_to_none=True)
    raw_output = model(batch.audio, batch.input_lengths)
    if not isinstance(raw_output, StudentOutput):
        raise TypeError("student model must return StudentOutput")
    losses = criterion(
        logits=raw_output.logits,
        student_hidden=raw_output.hidden,
        teacher_hidden=teacher_hidden,
        frame_lengths=raw_output.frame_lengths,
        padded_targets=batch.padded_targets,
        target_lengths=batch.target_lengths,
    )
    losses.total.backward()
    parameters = (*model.parameters(), *criterion.parameters())
    for parameter in parameters:
        if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
            raise FloatingPointError("non-finite distillation gradient")
    nn.utils.clip_grad_norm_(parameters, gradient_clip_norm)
    optimizer.step()
    return losses
