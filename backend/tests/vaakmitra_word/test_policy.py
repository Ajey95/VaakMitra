from __future__ import annotations

from dataclasses import dataclass
import pytest

from app.vaakmitra_word.contracts import AssessmentResult, Decision, ReasonCode
from app.vaakmitra_word.policy import (
    PolicyMode,
    SafeAdaptivePolicy,
    SessionPolicyState,
    TherapistConstraints,
)


def result(decision: Decision) -> AssessmentResult:
    probability = None if decision is Decision.UNSCORABLE else (0.95 if decision is Decision.PASS else 0.1)
    reason = {
        Decision.PASS: ReasonCode.CALIBRATED_TARGET_MATCH,
        Decision.RETRY: ReasonCode.CALIBRATED_WORD_MISMATCH,
        Decision.UNSCORABLE: ReasonCode.UNCERTAIN_RESULT,
    }[decision]
    return AssessmentResult(
        session_id="SES-1",
        attempt_id="ATT-1",
        word_id="TA-1",
        target_word="அம்மா",
        decision=decision,
        word_match_probability=probability,
        confidence=None if probability is None else 0.9,
        reason_code=reason,
    )


@dataclass
class UnsafeBandit:
    action: str = "outside_plan"

    def choose(self, _context, _eligible_actions):
        return type("Choice", (), {"action": self.action, "score": 99.0})()


def constraints() -> TherapistConstraints:
    return TherapistConstraints(
        allowed_actions=("repeat", "picture", "next_word", "break", "safe_end"),
        next_exercise_id="TA-2",
        max_retries=2,
    )


def test_stop_overrides_pass_and_bandit() -> None:
    state = SessionPolicyState(stop_requested=True)

    decision = SafeAdaptivePolicy().choose(
        result(Decision.PASS), state, constraints(), bandit=UnsafeBandit()
    )

    assert decision.next_action == "safe_end"
    assert decision.selected_by == "safety_override"


def test_unapproved_bandit_action_is_rejected() -> None:
    state = SessionPolicyState(context=(1.0, 0.0))

    decision = SafeAdaptivePolicy(mode=PolicyMode.ACTIVE).choose(
        result(Decision.RETRY), state, constraints(), bandit=UnsafeBandit()
    )

    assert decision.next_action == "repeat"
    assert decision.selected_by == "deterministic_fallback"


def test_shadow_choice_does_not_control_child() -> None:
    state = SessionPolicyState(context=(1.0, 0.0))
    bandit = UnsafeBandit(action="picture")

    decision = SafeAdaptivePolicy(mode=PolicyMode.SHADOW).choose(
        result(Decision.RETRY), state, constraints(), bandit=bandit
    )

    assert decision.next_action == "repeat"
    assert decision.shadow_action == "picture"


def test_max_retries_offer_break() -> None:
    state = SessionPolicyState(attempt_count=2)

    decision = SafeAdaptivePolicy().choose(result(Decision.RETRY), state, constraints())

    assert decision.next_action == "break"
    assert decision.response_intent == "OFFER_BREAK"


@pytest.mark.parametrize("reason", [ReasonCode.MODEL_TIMEOUT, ReasonCode.MODEL_INFERENCE_FAILED])
def test_section14_model_runtime_failure_requests_caregiver_help(reason) -> None:
    failed = AssessmentResult.unscorable(reason, session_id="SES-1", attempt_id="ATT-1",
        word_id="TA-1", target_word="அம்மா")
    decision = SafeAdaptivePolicy().choose(failed, SessionPolicyState(), constraints())
    assert decision.next_action == "break"
    assert decision.response_intent == "CAREGIVER_TECHNICAL_HELP"

