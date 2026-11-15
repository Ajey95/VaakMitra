"""DEC-028/029 and MST-004/011/012: mobile student architecture contracts."""

from __future__ import annotations

import math

import torch

from app.vaakmitra_word.mobile_student_model import MobileWordStudent, student_loss


def test_mst004_student_emits_finite_unit_embeddings_and_twenty_logits() -> None:
    torch.manual_seed(17)
    model = MobileWordStudent()
    embedding, logits = model(torch.linspace(-0.5, 0.5, 64_000).reshape(2, 32_000))
    assert embedding.shape == (2, 64)
    assert logits.shape == (2, 20)
    assert torch.isfinite(embedding).all()
    assert torch.isfinite(logits).all()
    assert torch.allclose(torch.linalg.vector_norm(embedding, dim=1), torch.ones(2), atol=1e-5)


def test_mst004_seeded_initialization_is_deterministic() -> None:
    waveform = torch.linspace(-0.2, 0.2, 32_000).reshape(1, -1)
    torch.manual_seed(29)
    first = MobileWordStudent().eval()(waveform)[1]
    torch.manual_seed(29)
    second = MobileWordStudent().eval()(waveform)[1]
    assert torch.equal(first, second)


def test_mst011_graph_normalization_is_invariant_to_dc_offset_and_safe_gain() -> None:
    waveform = (0.08 * torch.sin(torch.linspace(0.0, 80.0, 32_000))).reshape(1, -1)
    torch.manual_seed(31)
    model = MobileWordStudent().eval()
    original_embedding, original_logits = model(waveform)
    shifted_embedding, shifted_logits = model(waveform * 0.35 + 0.12)
    assert torch.allclose(original_embedding, shifted_embedding, atol=2e-5, rtol=2e-5)
    assert torch.allclose(original_logits, shifted_logits, atol=2e-5, rtol=2e-5)


def test_mst012_temporal_pooling_preserves_eight_ordered_regions() -> None:
    model = MobileWordStudent()
    assert model.temporal_pool.output_size == 8
    assert model.embedding.in_features == 96 * 8


def test_mst004_loss_is_exact_weighted_hard_and_teacher_objective() -> None:
    logits = torch.zeros((1, 2), requires_grad=True)
    hard_labels = torch.tensor([0])
    teacher = torch.tensor([[1.0, 0.0]])
    loss = student_loss(logits, hard_labels, teacher, temperature=2.0)
    assert float(loss.detach()) == pytest_approx(2.2 * math.log(2.0), absolute=1e-6)
    loss.backward()
    assert logits.grad is not None
    assert torch.count_nonzero(logits.grad).item() == 2


def test_mst004_loss_uses_hard_labels_when_teacher_target_is_missing() -> None:
    logits = torch.zeros((1, 2), requires_grad=True)
    loss = student_loss(logits, torch.tensor([1]), None, temperature=2.0)
    assert float(loss.detach()) == pytest_approx(math.log(2.0), absolute=1e-6)


def pytest_approx(expected: float, *, absolute: float):
    import pytest

    return pytest.approx(expected, abs=absolute)
