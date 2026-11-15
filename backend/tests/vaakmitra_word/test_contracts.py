from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.vaakmitra_word.contracts import (
    AssessmentResult,
    Decision,
    ReasonCode,
)


def result_fields() -> dict:
    return {
        "schema_version": "3.0.0",
        "session_id": "SES-0012",
        "attempt_id": "ATT-0031",
        "word_id": "TA_00021",
        "target_word": "அம்மா",
        "confidence": 0.9,
        "reason_code": ReasonCode.CALIBRATED_TARGET_MATCH,
        "response_intent": "CELEBRATE",
        "avatar_state": "CELEBRATE",
        "next_exercise_id": "TA_00022",
        "model_version": "model-1",
        "classifier_version": "classifier-1",
        "reference_bank_version": "references-1",
        "calibration_version": "calibration-1",
        "policy_version": "policy-1",
        "latency_ms": 50,
    }


def test_unscorable_legacy_mapping_has_no_numeric_score() -> None:
    result = AssessmentResult.unscorable(
        reason=ReasonCode.MODEL_UNAVAILABLE,
        session_id="SES-0012",
        attempt_id="ATT-0031",
        word_id="TA_00021",
        target_word="அம்மா",
    )

    legacy = result.to_legacy()

    assert legacy["matched"] is None
    assert legacy["accuracy"] is None
    assert legacy["capability"] == "model_unavailable"


def test_pass_requires_word_match_probability() -> None:
    with pytest.raises(ValidationError, match="word_match_probability"):
        AssessmentResult(
            decision=Decision.PASS,
            word_match_probability=None,
            **result_fields(),
        )


def test_probability_is_rejected_for_unscorable_result() -> None:
    fields = result_fields()
    fields["reason_code"] = ReasonCode.INSUFFICIENT_EVIDENCE
    fields["response_intent"] = "NEUTRAL_RETRY"
    fields["avatar_state"] = "COACH"

    with pytest.raises(ValidationError, match="must not expose"):
        AssessmentResult(
            decision=Decision.UNSCORABLE,
            word_match_probability=0.5,
            **fields,
        )

