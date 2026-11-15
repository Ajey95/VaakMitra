from __future__ import annotations

import numpy as np
import pytest

from app.vaakmitra_word.bandit import (
    InvalidRewardComponent,
    LinUCBPolicy,
    reward_value,
)


def test_linucb_updates_only_selected_action() -> None:
    policy = LinUCBPolicy(actions=("repeat", "picture"), dimension=2, alpha=0.25)
    before = policy.snapshot()

    policy.update("picture", np.array([1.0, 0.0]), {"successful_word": 1.0})
    after = policy.snapshot()

    assert np.array_equal(before["repeat"]["A"], after["repeat"]["A"])
    assert np.array_equal(before["repeat"]["b"], after["repeat"]["b"])
    assert not np.array_equal(before["picture"]["A"], after["picture"]["A"])


def test_time_seated_is_not_a_reward_component() -> None:
    with pytest.raises(InvalidRewardComponent, match="time_seated"):
        reward_value({"time_seated": 3.0})


def test_choose_never_returns_action_outside_eligible_set() -> None:
    policy = LinUCBPolicy(actions=("repeat", "picture"), dimension=2, alpha=0.25)

    choice = policy.choose(np.array([1.0, 0.0]), eligible_actions=("picture",))

    assert choice.action == "picture"


def test_context_dimension_mismatch_is_rejected() -> None:
    policy = LinUCBPolicy(actions=("repeat",), dimension=2)
    with pytest.raises(ValueError, match="dimension"):
        policy.choose(np.array([1.0]), eligible_actions=("repeat",))

