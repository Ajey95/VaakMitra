"""Clinician-constrained LinUCB policy primitives (NOV-02, RL-001..010)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


REWARD_WEIGHTS: dict[str, float] = {
    "successful_word": 1.0,
    "improvement_after_support": 0.5,
    "voluntary_continuation": 0.3,
    "return_after_break": 0.4,
    "repeated_failure": -0.5,
    "stop_request": -1.0,
    "abandonment": -1.0,
    "excessive_prompting": -0.5,
    "rejected_action": -1.0,
}


class InvalidRewardComponent(ValueError):
    pass


def reward_value(components: dict[str, float]) -> float:
    unknown = sorted(set(components) - set(REWARD_WEIGHTS))
    if unknown:
        raise InvalidRewardComponent(f"unsupported reward component: {', '.join(unknown)}")
    total = 0.0
    for name, amount in components.items():
        if not np.isfinite(amount):
            raise InvalidRewardComponent(f"reward component {name} must be finite")
        total += REWARD_WEIGHTS[name] * float(amount)
    return float(total)


@dataclass(frozen=True)
class BanditChoice:
    action: str
    score: float
    scores: dict[str, float]


class LinUCBPolicy:
    """Per-action disjoint LinUCB; callers supply an already-safe action set."""

    def __init__(
        self,
        *,
        actions: tuple[str, ...],
        dimension: int,
        alpha: float = 0.25,
        regularization: float = 1.0,
    ) -> None:
        if not actions or len(set(actions)) != len(actions):
            raise ValueError("actions must be non-empty and unique")
        if dimension <= 0 or alpha < 0 or regularization <= 0:
            raise ValueError("invalid LinUCB configuration")
        self.actions = actions
        self.dimension = dimension
        self.alpha = alpha
        self._state = {
            action: {
                "A": np.eye(dimension, dtype=np.float64) * regularization,
                "b": np.zeros(dimension, dtype=np.float64),
            }
            for action in actions
        }

    def choose(self, context: np.ndarray, eligible_actions: tuple[str, ...]) -> BanditChoice:
        vector = self._context(context)
        eligible = tuple(action for action in eligible_actions if action in self._state)
        if not eligible:
            raise ValueError("eligible_actions does not contain a configured action")
        scores: dict[str, float] = {}
        for action in eligible:
            matrix = self._state[action]["A"]
            target = self._state[action]["b"]
            inverse = np.linalg.inv(matrix)
            theta = inverse @ target
            uncertainty = float(np.sqrt(max(0.0, vector @ inverse @ vector)))
            scores[action] = float(theta @ vector + self.alpha * uncertainty)
        selected = max(eligible, key=lambda action: (scores[action], -eligible.index(action)))
        return BanditChoice(selected, scores[selected], scores)

    def update(self, action: str, context: np.ndarray, reward_components: dict[str, float]) -> None:
        if action not in self._state:
            raise ValueError(f"unknown action: {action}")
        vector = self._context(context)
        reward = reward_value(reward_components)
        self._state[action]["A"] += np.outer(vector, vector)
        self._state[action]["b"] += reward * vector

    def snapshot(self) -> dict[str, dict[str, np.ndarray]]:
        return {
            action: {"A": state["A"].copy(), "b": state["b"].copy()}
            for action, state in self._state.items()
        }

    def _context(self, context: np.ndarray) -> np.ndarray:
        vector = np.asarray(context, dtype=np.float64)
        if vector.shape != (self.dimension,):
            raise ValueError(f"context dimension must be {self.dimension}")
        if not np.isfinite(vector).all():
            raise ValueError("context must be finite")
        return vector

