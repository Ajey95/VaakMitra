"""
Sync allow-list — M3.4

Defines the exact set of fields that may appear in a sync packet.
Any field not in ALLOWED_SYNC_FIELDS raises SyncPolicyViolation.

This is the primary privacy enforcement gate for outbound data.

CRITICAL RULE: No audio, MFCC, embedding, phoneme-probability sequence,
transcript, spectrogram, or voice-derived representation may ever appear
in a sync packet. Adding such fields here requires a security review and
explicit therapist consent record update.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Allow-list (explicit; reject-by-default)
# ---------------------------------------------------------------------------

ALLOWED_SYNC_FIELDS: frozenset[str] = frozenset({
    # Identity (pseudonymous only)
    "pseudonym_id",
    "session_id",
    "attempt_id",
    "exercise_id",

    # Versioning (required by §6.2 invariant 7)
    "model_version",
    "dict_version",
    "policy_version",
    "consent_version",

    # Approved aggregate metrics
    "overall_pass",
    "session_duration_s",
    "syllable_scores_aggregate",  # aggregated syllable pass/fail counts only
    "total_attempts",
    "total_exercises",
    "timestamp_utc",
})

# ---------------------------------------------------------------------------
# Blocked field fragments (defence-in-depth substring check)
# ---------------------------------------------------------------------------

_BLOCKED_FRAGMENTS: frozenset[str] = frozenset({
    "audio",
    "mfcc",
    "embedding",
    "spectrogram",
    "phoneme_prob",
    "probability",
    "transcript",
    "voiceprint",
    "waveform",
    "pcm",
    "child_name",
    "device_id",
    "ip_address",
    "location",
    "gop",            # raw GOP scores are not synced; only aggregate pass/fail
    "confidence",     # raw confidence values are not synced
})


class SyncPolicyViolation(RuntimeError):
    """Raised when a sync packet contains a field not on the allow-list."""


def validate_sync_payload(payload: dict) -> None:
    """
    Validate that all keys in payload are on the allow-list and
    none match any blocked fragment.

    Raises
    ------
    SyncPolicyViolation
        If any key is not allowed or contains a blocked fragment.
    """
    for key in payload:
        key_lower = key.lower()

        # Check against allow-list
        if key not in ALLOWED_SYNC_FIELDS:
            raise SyncPolicyViolation(
                f"Sync packet field '{key}' is not on the allow-list. "
                "Only approved minimum therapy metrics may be synchronised. "
                "Add the field to ALLOWED_SYNC_FIELDS after security review."
            )

        # Defence-in-depth: block any field whose name contains a forbidden fragment
        for fragment in _BLOCKED_FRAGMENTS:
            if fragment in key_lower:
                raise SyncPolicyViolation(
                    f"Sync packet field '{key}' contains blocked fragment '{fragment}'. "
                    "This field may contain sensitive voice-derived data."
                )


def build_sync_payload(
    *,
    pseudonym_id: str,
    session_id: str,
    attempt_id: str,
    exercise_id: str,
    syllable_scores: list[dict],
    overall_pass: bool,
    model_version: str,
    dict_version: str,
    policy_version: str,
    session_duration_s: float | None = None,
    consent_version: str = "1.0",
) -> dict:
    """
    Build a validated sync payload from attempt data.

    Syllable scores are reduced to aggregate pass/fail counts only
    (not raw GOP or confidence values).
    """
    syllable_agg = {
        "pass_count": sum(1 for s in syllable_scores if s.get("status") == "pass"),
        "total_count": len(syllable_scores),
    }

    from datetime import datetime, timezone
    payload = {
        "pseudonym_id": pseudonym_id,
        "session_id": session_id,
        "attempt_id": attempt_id,
        "exercise_id": exercise_id,
        "overall_pass": overall_pass,
        "syllable_scores_aggregate": syllable_agg,
        "model_version": model_version,
        "dict_version": dict_version,
        "policy_version": policy_version,
        "consent_version": consent_version,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    if session_duration_s is not None:
        payload["session_duration_s"] = session_duration_s

    # Validate before returning
    validate_sync_payload(payload)
    return payload
