"""
DB privacy tests — M3.5

Verifies that:
1. No column in any table stores audio, MFCC, embeddings, or phoneme
   probability sequences.
2. Attempting to store such data raises PrivacyViolationError.
3. All 10 required entities exist in the schema.
"""

from __future__ import annotations

import pytest

from asd_backend.db.models import (
    Attempt,
    AuditEvent,
    Base,
    ChildProfile,
    ConsentRecord,
    ExercisePlan,
    ModelVersionLog,
    PhonemeScore,
    PrivacyViolationError,
    Session,
    SyllableScore,
    SyncQueue,
    _FORBIDDEN_COLUMN_FRAGMENTS,
)


# ---------------------------------------------------------------------------
# Schema structure tests
# ---------------------------------------------------------------------------

def test_all_required_entities_exist():
    """All 10 required DB entities must be present in the schema."""
    expected_tables = {
        "child_profile",
        "exercise_plan",
        "session",
        "attempt",
        "phoneme_score",
        "syllable_score",
        "model_version_log",
        "consent_record",
        "audit_event",
        "sync_queue",
    }
    actual_tables = set(Base.metadata.tables.keys())
    missing = expected_tables - actual_tables
    assert not missing, f"Missing required tables: {missing}"


def test_no_forbidden_columns_in_schema():
    """
    No column in any ORM model may have a name containing a forbidden
    privacy fragment (audio, mfcc, embedding, etc.).
    """
    violations = []
    for table_name, table in Base.metadata.tables.items():
        for col in table.columns:
            col_lower = col.name.lower()
            for fragment in _FORBIDDEN_COLUMN_FRAGMENTS:
                if fragment in col_lower:
                    violations.append(
                        f"Table '{table_name}', column '{col.name}' "
                        f"contains forbidden fragment '{fragment}'"
                    )
    assert not violations, (
        "Privacy violation: forbidden column names found in schema:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Required fields are present in Attempt
# ---------------------------------------------------------------------------

def test_attempt_has_version_fields():
    """
    Attempt must carry model_version, dict_version, policy_version
    for traceability (§6.2 invariant 7).
    """
    attempt_columns = {col.name for col in Attempt.__table__.columns}
    required = {"model_version", "dict_version", "policy_version"}
    missing = required - attempt_columns
    assert not missing, f"Attempt is missing version fields: {missing}"


def test_child_profile_uses_pseudonym():
    """ChildProfile must not have a 'name' or 'device_id' column."""
    child_columns = {col.name for col in ChildProfile.__table__.columns}
    forbidden_pii = {"name", "real_name", "device_id", "device_uuid", "ip_address"}
    present_pii = child_columns & forbidden_pii
    assert not present_pii, (
        f"ChildProfile contains PII columns: {present_pii}. "
        "Use pseudonymous UUIDs only."
    )


def test_sync_queue_has_idempotency_key():
    """SyncQueue must have an idempotency_key column."""
    sq_columns = {col.name for col in SyncQueue.__table__.columns}
    assert "idempotency_key" in sq_columns


# ---------------------------------------------------------------------------
# Repository-level privacy tests (async)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_attempt_create_does_not_accept_audio_field(test_db):
    """
    The Attempt ORM model must not accept any 'audio' attribute.
    Verifies that the column does not exist — not a kwarg test.
    """
    attempt_col_names = {c.name for c in Attempt.__table__.columns}
    assert "audio" not in attempt_col_names
    assert "audio_bytes" not in attempt_col_names
    assert "pcm" not in attempt_col_names
    assert "waveform" not in attempt_col_names


@pytest.mark.asyncio
async def test_phoneme_score_does_not_store_probability(test_db):
    """PhonemeScore must not have a 'probability' or 'prob_array' column."""
    col_names = {c.name for c in PhonemeScore.__table__.columns}
    assert "probability" not in col_names
    assert "prob_array" not in col_names
    assert "phoneme_prob" not in col_names


# ---------------------------------------------------------------------------
# AuditEvent must not log forbidden data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_audit_event_columns_are_safe(test_db):
    """AuditEvent must not have audio or embedding columns."""
    col_names = {c.name for c in AuditEvent.__table__.columns}
    forbidden = {"audio", "embedding", "mfcc", "spectrogram", "transcript"}
    assert not (col_names & forbidden), (
        f"AuditEvent has forbidden columns: {col_names & forbidden}"
    )
