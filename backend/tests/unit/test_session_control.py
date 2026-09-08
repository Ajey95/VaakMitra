from __future__ import annotations

from dataclasses import dataclass

import pytest
from modeling.training.session_control import (
    SessionBudget,
    next_frame_budget_after_oom,
)


@dataclass
class FakeClock:
    now: float

    def __call__(self) -> float:
        return self.now


def test_budget_requests_checkpoint_before_reserved_shutdown_window() -> None:
    clock = FakeClock(now=1_000.0)
    budget = SessionBudget(
        started_at=1_000.0,
        maximum_seconds=3_600,
        reserve_seconds=600,
        clock=clock,
    )
    clock.now = 4_001.0

    decision = budget.decision()

    assert decision.should_stop is True
    assert decision.reason == "session_time_budget"
    assert decision.seconds_remaining == pytest.approx(599.0)


def test_budget_continues_before_reserve_window() -> None:
    clock = FakeClock(now=100.0)
    budget = SessionBudget(100.0, 3_600, 600, clock)
    clock.now = 3_099.0

    decision = budget.decision()

    assert decision.should_stop is False
    assert decision.reason is None
    assert decision.seconds_remaining == pytest.approx(601.0)


def test_oom_budget_reduces_once_then_fails_closed() -> None:
    assert next_frame_budget_after_oom(480_000, retry_count=0) == 360_000

    with pytest.raises(RuntimeError, match="repeated CUDA out of memory"):
        next_frame_budget_after_oom(360_000, retry_count=1)


@pytest.mark.parametrize(
    ("maximum", "reserve", "message"),
    [
        (0, 0, "maximum session seconds must be positive"),
        (100, -1, "reserve seconds must be non-negative"),
        (100, 100, "reserve must be shorter"),
    ],
)
def test_invalid_session_budget_is_rejected(
    maximum: int,
    reserve: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        SessionBudget(0.0, maximum, reserve, FakeClock(0.0))


def test_clock_moving_backwards_is_rejected() -> None:
    clock = FakeClock(now=99.0)
    budget = SessionBudget(100.0, 3_600, 600, clock)

    with pytest.raises(RuntimeError, match="monotonic clock moved backwards"):
        budget.decision()
