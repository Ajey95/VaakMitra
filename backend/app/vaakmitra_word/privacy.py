"""Reject-by-default outbound metric schema (PRV-003..008)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


ALLOWED_SYNC_FIELDS = frozenset(
    {
        "schema_version",
        "event_id",
        "pseudonym_id",
        "session_id",
        "word_id",
        "decision",
        "attempt_count",
        "response_intent",
        "model_version",
        "classifier_version",
        "reference_bank_version",
        "calibration_version",
        "policy_version",
        "quality_category",
        "timestamp_bucket",
    }
)

BLOCKED_FRAGMENTS = frozenset(
    {
        "audio",
        "waveform",
        "pcm",
        "mfcc",
        "spectrogram",
        "embedding",
        "token",
        "transcript",
        "candidate",
        "voiceprint",
        "dtw",
        "probability",
        "confidence",
        "child_name",
        "free_text",
        "note",
        "ip_address",
        "location",
    }
)


class SyncPolicyViolation(ValueError):
    pass


def validate_sync_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise SyncPolicyViolation("sync payload must be an object")
    unknown = sorted(set(payload) - ALLOWED_SYNC_FIELDS)
    if unknown:
        raise SyncPolicyViolation(f"sync field is not allowed: {', '.join(unknown)}")
    _scan(payload, path="$")


def _scan(value, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            lowered = str(key).lower()
            for fragment in BLOCKED_FRAGMENTS:
                if fragment in lowered:
                    raise SyncPolicyViolation(f"forbidden voice/private field at {path}.{key}")
            _scan(nested, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _scan(nested, path=f"{path}[{index}]")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        raise SyncPolicyViolation(f"binary data is forbidden at {path}")

