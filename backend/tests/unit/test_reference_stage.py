from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
import torch
from modeling.training.batch_order import LengthRecord
from modeling.training.reference_stage import (
    GateDecision,
    run_reference_stage,
    should_run_full_stage,
    should_run_top_stage,
)
from modeling.training.session_control import SessionBudget
from torch import nn


class IdentityScaler:
    def __init__(self) -> None:
        self._steps = 0

    def scale(self, loss: torch.Tensor) -> torch.Tensor:
        return loss

    def unscale_(self, optimizer: torch.optim.Optimizer) -> None:
        del optimizer

    def step(self, optimizer: torch.optim.Optimizer) -> None:
        optimizer.step()
        self._steps += 1

    def update(self) -> None:
        return None

    def state_dict(self) -> dict[str, object]:
        return {"steps": self._steps}

    def load_state_dict(self, state: dict[str, object]) -> None:
        self._steps = int(state["steps"])


def _make_model(seed: int) -> nn.Module:
    torch.manual_seed(seed)
    return nn.Linear(1, 1)


def _run(
    root: Path,
    *,
    stop_after: int | None,
) -> tuple[nn.Module, int, str]:
    model = _make_model(17)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.02)
    scaler = IdentityScaler()
    records = tuple(LengthRecord(index, index + 1) for index in range(6))

    def train_batch(active_model: nn.Module, indexes: tuple[int, ...]) -> torch.Tensor:
        values = torch.tensor([[float(index + 1)] for index in indexes])
        targets = values * 0.4 + 0.2
        return nn.functional.mse_loss(active_model(values), targets)

    def evaluate(active_model: nn.Module) -> dict[str, float]:
        with torch.inference_mode():
            value = float(
                nn.functional.mse_loss(
                    active_model(torch.ones(1, 1)),
                    torch.tensor([[0.6]]),
                )
            )
        return {"phoneme_error_rate": value}

    result = run_reference_stage(
        model=model,
        optimizer=optimizer,
        scaler=scaler,
        stage="head_only",
        epochs=2,
        length_records=records,
        batch_size=1,
        bucket_size=3,
        seed=17,
        gradient_accumulation=1,
        binding_sha256="a" * 64,
        local_dir=root / "local",
        durable_dir=root / "durable",
        session_budget=SessionBudget(time.monotonic(), 3_600, 60, time.monotonic),
        train_batch=train_batch,
        evaluate_validation=evaluate,
        checkpoint_every_updates=2,
        stop_after_global_update=stop_after,
        status_path=root / "run-status.json",
    )
    return model, result.global_updates, result.status


def test_resumed_fixture_training_matches_uninterrupted_weights(tmp_path: Path) -> None:
    uninterrupted_model, uninterrupted_updates, uninterrupted_status = _run(
        tmp_path / "uninterrupted",
        stop_after=None,
    )
    _, stopped_updates, stopped_status = _run(tmp_path / "resumed", stop_after=2)
    resumed_model, resumed_updates, resumed_status = _run(
        tmp_path / "resumed",
        stop_after=None,
    )

    assert uninterrupted_status == "complete"
    assert stopped_status == "checkpointed_for_session_stop"
    assert stopped_updates == 2
    assert resumed_status == "complete"
    assert resumed_updates == uninterrupted_updates
    for name, value in uninterrupted_model.state_dict().items():
        assert torch.equal(value, resumed_model.state_dict()[name])


def test_restarting_completed_stage_keeps_valid_checkpoint_status(tmp_path: Path) -> None:
    root = tmp_path / "completed"
    _run(root, stop_after=None)
    _, _, status = _run(root, stop_after=None)

    report = json.loads((root / "run-status.json").read_text(encoding="utf-8"))
    assert status == "complete"
    assert len(report["checkpoint_sha256"]) == 64
    assert set(report["checkpoint_sha256"]) <= set("0123456789abcdef")


def test_full_stage_requires_metric_and_time_budget() -> None:
    allowed = should_run_full_stage(
        head_validation_per=0.40,
        top_validation_per=0.39,
        minimum_improvement=0.005,
        projected_seconds=7_200,
        available_seconds=8_000,
    )
    denied = should_run_full_stage(
        head_validation_per=0.40,
        top_validation_per=0.399,
        minimum_improvement=0.005,
        projected_seconds=7_200,
        available_seconds=8_000,
    )

    assert allowed.allowed is True
    assert denied == GateDecision(False, "validation_per_improvement_below_0.005")


def test_full_stage_is_denied_when_projected_time_does_not_fit() -> None:
    decision = should_run_full_stage(
        head_validation_per=0.40,
        top_validation_per=0.39,
        minimum_improvement=0.005,
        projected_seconds=8_001,
        available_seconds=8_000,
    )

    assert decision == GateDecision(False, "projected_stage_exceeds_available_time")


@pytest.mark.parametrize("invalid_per", [float("nan"), float("inf"), -0.1])
def test_full_stage_rejects_invalid_metrics(invalid_per: float) -> None:
    with pytest.raises(ValueError, match="phone error rates"):
        should_run_full_stage(
            head_validation_per=0.40,
            top_validation_per=invalid_per,
            minimum_improvement=0.005,
            projected_seconds=100,
            available_seconds=200,
        )


def test_top_stage_requires_reloadable_head_checkpoint_and_time() -> None:
    assert should_run_top_stage(
        head_checkpoint_reloadable=True,
        head_validation_per=0.4,
        projected_seconds=100,
        available_seconds=200,
    ).allowed
    assert should_run_top_stage(
        head_checkpoint_reloadable=False,
        head_validation_per=0.4,
        projected_seconds=100,
        available_seconds=200,
    ) == GateDecision(False, "head_checkpoint_not_reloadable")


def test_non_finite_training_loss_writes_sanitized_diagnostic(tmp_path: Path) -> None:
    model = _make_model(17)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.02)

    with pytest.raises(FloatingPointError, match="non-finite training loss"):
        run_reference_stage(
            model=model,
            optimizer=optimizer,
            scaler=IdentityScaler(),
            stage="head_only",
            epochs=1,
            length_records=(LengthRecord(0, 1),),
            batch_size=1,
            bucket_size=1,
            seed=17,
            gradient_accumulation=1,
            binding_sha256="a" * 64,
            local_dir=tmp_path / "local",
            durable_dir=tmp_path / "durable",
            session_budget=SessionBudget(time.monotonic(), 3_600, 60, time.monotonic),
            train_batch=lambda _model, _indexes: torch.tensor(float("nan"), requires_grad=True),
            evaluate_validation=lambda _model: {"phoneme_error_rate": 1.0},
            checkpoint_every_updates=2,
            status_path=tmp_path / "run-status.json",
        )

    diagnostic = (tmp_path / "durable" / "diagnostic-failure.json").read_text(
        encoding="utf-8"
    )
    assert "non_finite_training_loss" in diagnostic
    assert "audio" not in diagnostic
    assert "transcript" not in diagnostic
    assert "target" not in diagnostic
