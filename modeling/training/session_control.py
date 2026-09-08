"""Monotonic session budgets and bounded CUDA out-of-memory recovery."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class StopDecision:
    should_stop: bool
    reason: str | None
    elapsed_seconds: float
    seconds_remaining: float


class SessionBudget:
    """Request a graceful stop before the runtime termination window."""

    def __init__(
        self,
        started_at: float,
        maximum_seconds: int,
        reserve_seconds: int,
        clock: Clock,
    ) -> None:
        if maximum_seconds <= 0:
            raise ValueError("maximum session seconds must be positive")
        if reserve_seconds < 0:
            raise ValueError("reserve seconds must be non-negative")
        if reserve_seconds >= maximum_seconds:
            raise ValueError("reserve must be shorter than maximum session time")
        self._started_at = float(started_at)
        self._maximum_seconds = float(maximum_seconds)
        self._reserve_seconds = float(reserve_seconds)
        self._clock = clock

    def decision(self) -> StopDecision:
        now = float(self._clock())
        if now < self._started_at:
            raise RuntimeError("monotonic clock moved backwards")
        elapsed = now - self._started_at
        remaining = max(0.0, self._maximum_seconds - elapsed)
        should_stop = remaining <= self._reserve_seconds
        return StopDecision(
            should_stop=should_stop,
            reason="session_time_budget" if should_stop else None,
            elapsed_seconds=elapsed,
            seconds_remaining=remaining,
        )


def next_frame_budget_after_oom(current: int, *, retry_count: int) -> int:
    """Reduce the frame budget once; repeated CUDA OOM aborts the stage."""

    if current <= 0:
        raise ValueError("current frame budget must be positive")
    if retry_count < 0:
        raise ValueError("OOM retry count must be non-negative")
    if retry_count > 0:
        raise RuntimeError("repeated CUDA out of memory")
    return max(1, current * 3 // 4)
