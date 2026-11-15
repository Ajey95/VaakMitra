"""GOV-004: a candidate suite cannot become approved from a boolean flip."""

import pytest

from app.vaakmitra_word.canary import CanarySuite, approve_canary_suite, verify_approved_canary_suite, CanaryError
from app.vaakmitra_word.review_exports import sign_review_export


KEY = "test-review-key-with-at-least-32-characters"


def _suite():
    rows = []
    for index, category, decision in (
        (1, "positive", "PASS"), (2, "confusable", "RETRY"),
        (3, "audio_quality_negative", "UNSCORABLE"),
    ):
        rows.append({
            "canary_id": f"canary-{index}", "source_sample_id": f"sample-{index}",
            "category": category, "word_id": "TA_WORD_0001", "target_word": "தமிழ்",
            "audio_path": f"{index}.wav", "audio_sha256": str(index) * 64,
            "expected_decision": decision, "allowed_reason_codes": ("REASON",),
            "consent_basis": "public_dataset", "reviewer_id": "candidate-only",
        })
    return CanarySuite(
        schema_version="vaakmitra-canary-suite-1", vocabulary_hash="a" * 64,
        dataset_manifest_hash="b" * 64, positive_words=("TA_WORD_0001",),
        categories=("audio_quality_negative", "confusable", "positive"),
        records=tuple(rows),
    )


def _export(suite, **changes):
    payload = {
        "schema_version": "vaakmitra-review-export-1", "kind": "canary",
        "manifest_sha256": "c" * 64, "human_approved": True,
        "items": [{
            "item_id": row.canary_id, "word_id": row.word_id,
            "source_sample_id": row.source_sample_id,
            "audio_sha256": row.audio_sha256,
            "category": row.category,
            "expected_decision": row.expected_decision,
            "observed_sha256": row.audio_sha256, "reviewer_id": "human-therapist",
        } for row in suite.records],
    }
    payload.update(changes)
    return sign_review_export(payload, KEY)


def test_gov004_exact_signed_review_can_finalize_candidate():
    suite = _suite()
    approved = approve_canary_suite(suite, _export(suite), "c" * 64, KEY)
    assert approved.human_approved is True
    assert all(row.reviewer_id == "human-therapist" for row in approved.records)
    assert verify_approved_canary_suite(approved, KEY) is True
    assert verify_approved_canary_suite(CanarySuite.model_validate_json(approved.model_dump_json()), KEY) is True


def test_gov004_boolean_flip_and_changed_record_do_not_verify():
    suite = _suite()
    forged = suite.model_copy(update={"human_approved": True})
    assert verify_approved_canary_suite(forged, KEY) is False
    approved = approve_canary_suite(suite, _export(suite), "c" * 64, KEY)
    changed = approved.model_copy(update={"records": (approved.records[0].model_copy(
        update={"audio_sha256": "f" * 64}), *approved.records[1:])})
    assert verify_approved_canary_suite(changed, KEY) is False
    assert verify_approved_canary_suite(approved, "wrong-secret-with-at-least-32-characters") is False


def test_gov004_tampered_audio_or_wrong_suite_fails_closed():
    suite = _suite()
    approval = _export(suite)
    approval["items"][0]["audio_sha256"] = "f" * 64
    with pytest.raises(CanaryError, match="canary_review_signature_invalid"):
        approve_canary_suite(suite, approval, "c" * 64, KEY)
    with pytest.raises(CanaryError, match="canary_review_suite_mismatch"):
        approve_canary_suite(suite, _export(suite), "d" * 64, KEY)
