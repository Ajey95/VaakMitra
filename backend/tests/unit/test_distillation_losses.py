from __future__ import annotations

import pytest
import torch
from modeling.distillation.losses import (
    DistillationCriterion,
    DistillationWeights,
    masked_representation_loss,
    relational_frame_loss,
    validate_teacher_cache_binding,
)
from modeling.distillation.teacher_features import TeacherFeatureManifest
from pydantic import ValidationError


def _manifest() -> TeacherFeatureManifest:
    return TeacherFeatureManifest(
        schema_version="1.0",
        model_id="ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large",
        model_revision="a" * 40,
        model_license_spdx="MIT",
        sample_rate_hz=16_000,
        frame_shift_ms=10.0,
        frame_count=2,
        feature_dimension=3,
        audio_sha256="b" * 64,
        feature_sha256="c" * 64,
        source_scope="adult_tamil_teacher",
        storage_policy="local_only_voice_derived",
        direct_phoneme_posteriors_supported=False,
    )


def test_masked_representation_loss_ignores_padded_frames() -> None:
    student = torch.tensor([[[1.0], [9.0]]])
    teacher = torch.tensor([[[0.0], [100.0]]])

    loss = masked_representation_loss(
        student, teacher, torch.tensor([[True, False]])
    )

    assert float(loss) == pytest.approx(0.5)


def test_masked_representation_loss_rejects_empty_mask_and_shape_mismatch() -> None:
    with pytest.raises(ValueError, match="valid frame"):
        masked_representation_loss(
            torch.zeros(1, 2, 3),
            torch.zeros(1, 2, 3),
            torch.tensor([[False, False]]),
        )
    with pytest.raises(ValueError, match="same shape"):
        masked_representation_loss(
            torch.zeros(1, 2, 3),
            torch.zeros(1, 2, 4),
            torch.tensor([[True, True]]),
        )


def test_relational_loss_is_zero_for_identical_valid_representations() -> None:
    hidden = torch.tensor([[[1.0, 0.0], [0.0, 1.0], [9.0, 9.0]]])
    mask = torch.tensor([[True, True, False]])

    loss = relational_frame_loss(hidden, hidden.clone(), mask)

    assert float(loss) == pytest.approx(0.0)


def test_distillation_weights_reject_text_posterior_kl_and_all_zero_weights() -> None:
    with pytest.raises(ValidationError, match="text_posterior_kl"):
        DistillationWeights.model_validate(
            {
                "supervised_ctc": 1.0,
                "representation": 1.0,
                "relational": 0.0,
                "sequence_consistency": 0.0,
                "text_posterior_kl": 1.0,
            }
        )
    with pytest.raises(ValidationError, match="positive"):
        DistillationWeights(
            supervised_ctc=0.0,
            representation=0.0,
            relational=0.0,
            sequence_consistency=0.0,
        )


def test_criterion_combines_finite_ctc_and_hidden_losses() -> None:
    criterion = DistillationCriterion(
        student_dimension=2,
        teacher_dimension=3,
        weights=DistillationWeights(
            supervised_ctc=1.0,
            representation=0.5,
            relational=0.25,
            sequence_consistency=0.0,
        ),
        blank_index=0,
    )
    logits = torch.tensor(
        [[[0.0, 3.0, 0.0], [3.0, 0.0, 0.0], [0.0, 0.0, 3.0]]],
        requires_grad=True,
    )
    student_hidden = torch.ones(1, 3, 2, requires_grad=True)
    teacher_hidden = torch.ones(1, 3, 3)

    result = criterion(
        logits=logits,
        student_hidden=student_hidden,
        teacher_hidden=teacher_hidden,
        frame_lengths=torch.tensor([3]),
        padded_targets=torch.tensor([[1, 2]]),
        target_lengths=torch.tensor([2]),
    )
    result.total.backward()

    assert torch.isfinite(result.total)
    assert result.total >= result.supervised_ctc
    assert student_hidden.grad is not None


def test_teacher_cache_binding_rejects_revision_or_audio_mismatch() -> None:
    validate_teacher_cache_binding(
        _manifest(), expected_revision="a" * 40, expected_audio_sha256="b" * 64
    )
    with pytest.raises(ValueError, match="revision"):
        validate_teacher_cache_binding(
            _manifest(), expected_revision="d" * 40, expected_audio_sha256="b" * 64
        )
    with pytest.raises(ValueError, match="audio"):
        validate_teacher_cache_binding(
            _manifest(), expected_revision="a" * 40, expected_audio_sha256="d" * 64
        )
