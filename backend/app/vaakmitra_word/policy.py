"""Safety-first deterministic and optional bandit policy (DEC-011, Section 14)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import numpy as np

from .contracts import AssessmentResult, Decision, ReasonCode


class PolicyMode(str, Enum):
    DETERMINISTIC = "deterministic"
    SHADOW = "shadow"
    ACTIVE = "active"


@dataclass(frozen=True)
class TherapistConstraints:
    allowed_actions: tuple[str, ...]
    next_exercise_id: str
    max_retries: int = 2


@dataclass
class SessionPolicyState:
    attempt_count: int = 0
    stop_requested: bool = False
    break_requested: bool = False
    context: tuple[float, ...] = ()


@dataclass(frozen=True)
class PolicyDecision:
    response_intent: str
    avatar_state: str
    next_action: str
    next_exercise_id: str | None
    selected_by: str
    override_reason: str | None = None
    shadow_action: str | None = None


class BanditProtocol(Protocol):
    def choose(self, context: np.ndarray, eligible_actions: tuple[str, ...]): ...


class SafeAdaptivePolicy:
    version = "ta-safe-policy-1.0.0"

    def __init__(self, mode: PolicyMode = PolicyMode.DETERMINISTIC) -> None:
        self.mode = mode

    def choose(
        self,
        result: AssessmentResult,
        state: SessionPolicyState,
        constraints: TherapistConstraints,
        bandit: BanditProtocol | None = None,
    ) -> PolicyDecision:
        allowed = set(constraints.allowed_actions)
        if state.stop_requested:
            return self._safety("CALM_END", "END", "safe_end", None, allowed, "stop_requested")
        if state.break_requested:
            return self._safety("OFFER_BREAK", "BREAK", "break", None, allowed, "break_requested")
        if result.decision is Decision.RETRY and state.attempt_count >= constraints.max_retries:
            return self._safety("OFFER_BREAK", "BREAK", "break", None, allowed, "max_retries")

        default_action, intent, avatar, eligible = self._deterministic(result, allowed)
        selected_by = "deterministic"
        shadow_action: str | None = None

        if bandit is not None and state.context and eligible and self.mode is not PolicyMode.DETERMINISTIC:
            choice = bandit.choose(np.asarray(state.context, dtype=np.float64), eligible)
            if self.mode is PolicyMode.SHADOW:
                shadow_action = choice.action if choice.action in eligible else None
            elif choice.action in eligible:
                default_action = choice.action
                selected_by = "bandit"
            else:
                selected_by = "deterministic_fallback"

        return PolicyDecision(
            response_intent=self._intent_for(default_action, intent),
            avatar_state=self._avatar_for(default_action, avatar),
            next_action=default_action,
            next_exercise_id=constraints.next_exercise_id if default_action == "next_word" else None,
            selected_by=selected_by,
            shadow_action=shadow_action,
        )

    @staticmethod
    def _deterministic(
        result: AssessmentResult,
        allowed: set[str],
    ) -> tuple[str, str, str, tuple[str, ...]]:
        if result.decision is Decision.PASS:
            action = "next_word" if "next_word" in allowed else "safe_end"
            return action, "CELEBRATE", "CELEBRATE", (action,)
        if result.decision is Decision.UNSCORABLE:
            capability_reasons = {
                ReasonCode.MODEL_UNAVAILABLE,
                ReasonCode.MODEL_INTEGRITY_MISMATCH,
                ReasonCode.CALIBRATION_UNAVAILABLE,
                ReasonCode.ARTIFACT_MISMATCH,
                ReasonCode.MODEL_TIMEOUT,
                ReasonCode.MODEL_INFERENCE_FAILED,
                ReasonCode.VAD_UNAVAILABLE,
                ReasonCode.CLASSIFIER_UNAVAILABLE,
                ReasonCode.REFERENCE_UNAVAILABLE,
            }
            if result.reason_code in capability_reasons:
                action = "break" if "break" in allowed else "safe_end"
                return action, "CAREGIVER_TECHNICAL_HELP", "BREAK", (action,)
            action = "repeat" if "repeat" in allowed else "break"
            return action, "NEUTRAL_RETRY", "COACH", (action,)

        eligible = tuple(
            action for action in ("repeat", "picture", "adult_example", "easier_word")
            if action in allowed
        )
        action = "repeat" if "repeat" in eligible else eligible[0] if eligible else "break"
        return action, "ENCOURAGE_RETRY", "COACH", eligible or (action,)

    @staticmethod
    def _intent_for(action: str, fallback: str) -> str:
        return {
            "picture": "SHOW_PICTURE_SUPPORT",
            "adult_example": "PLAY_APPROVED_EXAMPLE",
            "easier_word": "SWITCH_APPROVED_WORD",
        }.get(action, fallback)

    @staticmethod
    def _avatar_for(action: str, fallback: str) -> str:
        return "SPEAKING" if action == "adult_example" else fallback

    @staticmethod
    def _safety(
        intent: str,
        avatar: str,
        preferred_action: str,
        next_exercise_id: str | None,
        allowed: set[str],
        reason: str,
    ) -> PolicyDecision:
        action = preferred_action if preferred_action in allowed else "safe_end"
        return PolicyDecision(
            response_intent=intent,
            avatar_state=avatar,
            next_action=action,
            next_exercise_id=next_exercise_id,
            selected_by="safety_override",
            override_reason=reason,
        )

