"""
Sync allow-list and packet inspection tests — M3.5

Verifies that:
1. Packets with forbidden fields are rejected.
2. Approved fields pass validation.
3. build_sync_payload produces only allowed fields.
4. Packet serialisation contains no forbidden key.
"""

from __future__ import annotations

import json

import pytest

from asd_backend.sync.allow_list import (
    ALLOWED_SYNC_FIELDS,
    SyncPolicyViolation,
    build_sync_payload,
    validate_sync_payload,
)


# ---------------------------------------------------------------------------
# Allowed fields pass
# ---------------------------------------------------------------------------

def test_valid_payload_passes():
    """A payload with only allowed fields must pass validation."""
    payload = {
        "pseudonym_id": "child-uuid-001",
        "session_id": "SES-0001",
        "attempt_id": "ATT-0001",
        "exercise_id": "TA_AMMA_01",
        "overall_pass": True,
        "syllable_scores_aggregate": {"pass_count": 2, "total_count": 2},
        "model_version": "ta-ctc-1.0.0",
        "dict_version": "ta-dict-1.0.0",
        "policy_version": "1.0.0",
        "consent_version": "1.0",
        "timestamp_utc": "2026-01-01T00:00:00+00:00",
    }
    # Should not raise
    validate_sync_payload(payload)


# ---------------------------------------------------------------------------
# Forbidden fields are rejected
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("forbidden_field", [
    "audio_bytes",
    "mfcc_array",
    "embedding_vector",
    "phoneme_prob_sequence",
    "spectrogram_data",
    "transcript",
    "voiceprint",
    "waveform",
    "pcm_data",
    "child_name",
    "device_id",
    "ip_address",
    "gop_scores",
    "confidence_raw",
])
def test_forbidden_field_raises(forbidden_field: str):
    """Any field not on the allow-list must raise SyncPolicyViolation."""
    payload = {
        "pseudonym_id": "child-uuid-001",
        forbidden_field: "some_value",
    }
    with pytest.raises(SyncPolicyViolation):
        validate_sync_payload(payload)


# ---------------------------------------------------------------------------
# build_sync_payload produces only allowed fields
# ---------------------------------------------------------------------------

def test_build_sync_payload_only_allowed_fields():
    """
    build_sync_payload must produce a payload where every key is in
    ALLOWED_SYNC_FIELDS. This is the packet inspection test.
    """
    payload = build_sync_payload(
        pseudonym_id="child-uuid-001",
        session_id="SES-0001",
        attempt_id="ATT-0001",
        exercise_id="TA_AMMA_01",
        syllable_scores=[
            {"syllable": "அம்", "score": 0.86, "status": "pass"},
            {"syllable": "மா",  "score": 0.56, "status": "coach"},
        ],
        overall_pass=False,
        model_version="ta-ctc-1.0.0",
        dict_version="ta-dict-1.0.0",
        policy_version="1.0.0",
        session_duration_s=45.2,
    )

    # All keys must be on the allow-list
    disallowed = set(payload.keys()) - ALLOWED_SYNC_FIELDS
    assert not disallowed, (
        f"Sync payload contains disallowed fields: {disallowed}\n"
        f"Full payload keys: {list(payload.keys())}"
    )


def test_build_sync_payload_no_raw_gop():
    """
    build_sync_payload must NOT include raw GOP scores or confidence values.
    Only aggregate pass/fail counts are allowed.
    """
    payload = build_sync_payload(
        pseudonym_id="child-uuid-001",
        session_id="SES-0001",
        attempt_id="ATT-0001",
        exercise_id="TA_AMMA_01",
        syllable_scores=[
            {"syllable": "அம்", "score": 0.86, "status": "pass", "gop": 0.90},
            {"syllable": "மா",  "score": 0.56, "status": "coach", "gop": 0.50},
        ],
        overall_pass=False,
        model_version="ta-ctc-1.0.0",
        dict_version="ta-dict-1.0.0",
        policy_version="1.0.0",
    )

    # Serialise to JSON (simulates packet transmission)
    packet_json = json.dumps(payload)
    packet_lower = packet_json.lower()

    # Ensure no raw score data appears in the serialised packet
    assert "gop" not in packet_lower, "Serialised packet contains raw GOP scores"
    assert '"score"' not in packet_lower, "Serialised packet contains raw score values"
    assert "confidence" not in packet_lower, "Serialised packet contains confidence values"
    assert "audio" not in packet_lower
    assert "embedding" not in packet_lower
    assert "mfcc" not in packet_lower


def test_syllable_scores_reduced_to_aggregate():
    """
    Syllable scores must be reduced to pass_count/total_count aggregates
    — not raw score values.
    """
    payload = build_sync_payload(
        pseudonym_id="child-uuid-001",
        session_id="SES-0001",
        attempt_id="ATT-0001",
        exercise_id="TA_AMMA_01",
        syllable_scores=[
            {"syllable": "அம்", "score": 0.86, "status": "pass"},
            {"syllable": "மா",  "score": 0.56, "status": "coach"},
            {"syllable": "ப",   "score": 0.30, "status": "retry"},
        ],
        overall_pass=False,
        model_version="ta-ctc-1.0.0",
        dict_version="ta-dict-1.0.0",
        policy_version="1.0.0",
    )

    agg = payload["syllable_scores_aggregate"]
    assert agg["total_count"] == 3
    assert agg["pass_count"] == 1  # only "அம்" passed


# ---------------------------------------------------------------------------
# Extra field injection attempt
# ---------------------------------------------------------------------------

def test_extra_field_beyond_allowed_raises():
    """Unexpected field injected into a valid payload raises SyncPolicyViolation."""
    payload = {
        "pseudonym_id": "child-uuid-001",
        "session_id": "SES-0001",
        "attempt_id": "ATT-0001",
        "exercise_id": "TA_AMMA_01",
        "overall_pass": True,
        "model_version": "ta-ctc-1.0.0",
        "dict_version": "ta-dict-1.0.0",
        "policy_version": "1.0.0",
        "consent_version": "1.0",
        "timestamp_utc": "2026-01-01T00:00:00+00:00",
        "syllable_scores_aggregate": {"pass_count": 1, "total_count": 1},
        "unexpected_extra_field": "oops",  # should be rejected
    }
    with pytest.raises(SyncPolicyViolation):
        validate_sync_payload(payload)
