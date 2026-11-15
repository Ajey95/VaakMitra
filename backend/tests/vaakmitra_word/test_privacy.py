from __future__ import annotations

import pytest

from app.vaakmitra_word.privacy import SyncPolicyViolation, validate_sync_payload


def valid_payload() -> dict:
    return {
        "schema_version": "3.0.0",
        "event_id": "EV-1",
        "pseudonym_id": "P-1",
        "session_id": "SES-1",
        "word_id": "TA-1",
        "decision": "PASS",
        "attempt_count": 1,
        "response_intent": "CELEBRATE",
        "model_version": "model-1",
        "classifier_version": "classifier-1",
        "reference_bank_version": "references-1",
        "calibration_version": "calibration-1",
        "policy_version": "policy-1",
        "quality_category": "acceptable",
        "timestamp_bucket": "2026-09-06",
    }


def test_documented_aggregate_payload_is_allowed() -> None:
    validate_sync_payload(valid_payload())


@pytest.mark.parametrize(
    "payload",
    [
        {"metadata": {"audio": "x"}},
        {"items": [{"embedding_vector": [1, 2]}]},
        {"transcript": "அம்மா"},
        {"word_match_probability": 0.91},
    ],
)
def test_forbidden_data_is_rejected_at_any_depth(payload: dict) -> None:
    candidate = valid_payload()
    candidate.update(payload)

    with pytest.raises(SyncPolicyViolation):
        validate_sync_payload(candidate)


def test_unknown_top_level_field_is_rejected() -> None:
    payload = valid_payload()
    payload["caregiver_note"] = "free text"
    with pytest.raises(SyncPolicyViolation, match="not allowed"):
        validate_sync_payload(payload)

