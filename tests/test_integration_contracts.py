"""Cross-team contracts: these tests catch incompatible teammate payloads."""

import pytest
from pydantic import ValidationError

from asd_backend.contracts import (
    AlignmentResult,
    CaptureStatus,
    PhonemeAlignment,
    ScoringResult,
)
from asd_backend.session.api import init_orchestrator


def test_member1_alignment_contract_accepts_documented_payload():
    result = AlignmentResult.model_validate({
        "contract_version": "1.0",
        "attempt_id": "ATT-00031",
        "capture_status": "valid",
        "expected_word": "அம்மா",
        "expected_phonemes": ["a", "m", "m", "a:"],
        "phoneme_alignment": [
            {"phoneme": "a", "start_ms": 40, "end_ms": 160, "confidence": 0.91}
        ],
        "alignment_confidence": 0.85,
        "dictionary_version": "ta-dict-1.0.0",
    })
    assert result.capture_status is CaptureStatus.VALID
    assert result.phoneme_alignment[0].duration_ms == 120


def test_alignment_contract_rejects_backwards_timestamps():
    with pytest.raises(ValidationError):
        PhonemeAlignment(
            phoneme="a", start_ms=160, end_ms=40, confidence=0.91
        )


def test_member2_contract_rejects_unknown_fields_to_prevent_silent_drift():
    with pytest.raises(ValidationError):
        ScoringResult.model_validate({
            "contract_version": "1.0",
            "attempt_id": "ATT-1",
            "model_version": "ta-ctc-1",
            "phoneme_scores": [],
            "syllable_scores": [],
            "overall_confidence": 0.5,
            "raw_embedding": [1, 2, 3],
        })


def test_application_composition_injects_teammate_services(default_policy):
    class Member1:
        async def process(self, audio_bytes, target_word, exercise_id):
            raise AssertionError("not called")

    class Member2:
        model_version = "member2-real-1.0"

        async def score(self, audio_bytes, phoneme_alignment, expected_phonemes, attempt_id):
            raise AssertionError("not called")

    member1, member2 = Member1(), Member2()
    orchestrator = init_orchestrator(
        policy=default_policy, member1=member1, member2=member2
    )
    assert orchestrator.member1 is member1
    assert orchestrator.member2 is member2
