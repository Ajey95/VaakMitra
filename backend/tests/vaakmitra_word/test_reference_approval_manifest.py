"""GOV-003: a forged or stale approval file cannot activate an adult reference."""

import pytest

from app.vaakmitra_word.corpus import CorpusRecord
from app.vaakmitra_word.review_exports import sign_review_export
from scripts.model.build_reference_bank import validate_approval_manifest


SOURCE = CorpusRecord(
    schema_version="vaakmitra-corpus-record-1",
    sample_id="source-1",
    source_id="public-a",
    source_revision="v1",
    original_id="clip-1",
    speaker_pseudonym="speaker-1",
    canonical_word_id="TA_WORD_0001",
    label_kind="target",
    audio_path="clip.wav",
    audio_sha256="a" * 64,
    duration_seconds=1.0,
    split="reference",
    licence_id="public-licence",
)


def _approval(**changes):
    item = {
        "sample_id": "source-1",
        "canonical_word_id": "TA_WORD_0001",
        "audio_sha256": "a" * 64,
        "approved": True,
        "capture_valid": True,
        "quality_score": 0.8,
        "review_provenance": "qualified_human",
        "reviewer_qualified": True,
        "reviewer_id": "reviewer-1",
    }
    item.update(changes)
    return item


@pytest.fixture(autouse=True)
def signing_key(monkeypatch):
    monkeypatch.setenv("VAAKMITRA_REVIEW_SIGNING_KEY", "test-review-key-with-at-least-32-characters")


def _manifest(**changes):
    payload = {
        "schema_version": "vaakmitra-reference-approvals-1",
        "dataset_manifest_hash": "b" * 64,
        "human_approved": True,
        "approvals": [_approval()],
    }
    payload.update(changes)
    return sign_review_export(payload, "test-review-key-with-at-least-32-characters")


def test_gov003_rejects_unapproved_global_manifest():
    with pytest.raises(RuntimeError, match="approval_manifest_human_review_required"):
        validate_approval_manifest(_manifest(human_approved=False), {SOURCE.sample_id: SOURCE}, "b" * 64)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"audio_sha256": "c" * 64}, "approval_audio_hash_mismatch"),
        ({"canonical_word_id": "TA_WORD_0002"}, "approval_word_mismatch"),
        ({"capture_valid": False}, "approval_capture_invalid"),
        ({"review_provenance": "ai_draft"}, "approval_qualified_human_required"),
        ({"reviewer_qualified": False}, "approval_qualified_human_required"),
        ({"quality_score": 1.5}, "approval_quality_invalid"),
    ],
)
def test_gov003_rejects_invalid_per_sample_review(change, reason):
    with pytest.raises(RuntimeError, match=reason):
        validate_approval_manifest(_manifest(approvals=[_approval(**change)]), {SOURCE.sample_id: SOURCE}, "b" * 64)


def test_gov003_rejects_duplicate_or_unknown_samples():
    with pytest.raises(RuntimeError, match="approval_sample_duplicate"):
        validate_approval_manifest(_manifest(approvals=[_approval(), _approval()]), {SOURCE.sample_id: SOURCE}, "b" * 64)
    with pytest.raises(RuntimeError, match="approval_sample_unknown"):
        validate_approval_manifest(_manifest(approvals=[_approval(sample_id="unknown")]), {SOURCE.sample_id: SOURCE}, "b" * 64)


def test_gov003_accepts_exact_hash_bound_qualified_review():
    approvals = validate_approval_manifest(_manifest(), {SOURCE.sample_id: SOURCE}, "b" * 64)
    assert approvals["source-1"]["quality_score"] == 0.8


def test_gov003_tampered_approval_signature_is_rejected():
    payload = _manifest()
    payload["approvals"][0]["quality_score"] = 1.0
    with pytest.raises(RuntimeError, match="approval_manifest_signature_invalid"):
        validate_approval_manifest(payload, {SOURCE.sample_id: SOURCE}, "b" * 64)


def test_gov003_duplicate_audio_or_cross_split_source_cannot_enter_bank():
    duplicate = SOURCE.model_copy(update={"sample_id": "source-2", "speaker_pseudonym": "speaker-2"})
    with pytest.raises(RuntimeError, match="approval_audio_duplicate"):
        validate_approval_manifest(
            _manifest(approvals=[_approval(), _approval(sample_id="source-2")]),
            {SOURCE.sample_id: SOURCE, duplicate.sample_id: duplicate}, "b" * 64,
        )
    evaluation_copy = SOURCE.model_copy(update={"sample_id": "eval-1", "split": "evaluation"})
    with pytest.raises(RuntimeError, match="approval_audio_cross_split"):
        validate_approval_manifest(
            _manifest(), {SOURCE.sample_id: SOURCE, evaluation_copy.sample_id: evaluation_copy}, "b" * 64,
        )
