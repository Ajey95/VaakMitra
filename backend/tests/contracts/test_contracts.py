from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from vaakmitra.contracts.acoustic import AcousticOutput
from vaakmitra.contracts.alignment import AlignedPhoneme, AlignmentResult
from vaakmitra.contracts.scoring import AssessmentResult


def test_acoustic_output_rejects_probability_width_mismatch() -> None:
    with pytest.raises(ValidationError, match="vocabulary_size"):
        AcousticOutput(
            log_probabilities=np.zeros((2, 3), dtype=np.float32),
            frame_shift_ms=20.0,
            model_version="ta-ctc-1.0.0",
            vocabulary_version="ta-phones-1.0.0",
            blank_index=0,
            vocabulary_size=4,
        )


def test_alignment_rejects_empty_frame_segment() -> None:
    with pytest.raises(ValidationError, match="end_frame"):
        AlignedPhoneme(
            phoneme="a",
            start_frame=2,
            end_frame=2,
            start_ms=40.0,
            end_ms=60.0,
            confidence=0.9,
        )


def test_alignment_result_requires_phonemes_when_valid() -> None:
    with pytest.raises(ValidationError, match="phonemes"):
        AlignmentResult(status="valid", confidence=0.9, phonemes=())


def test_assessment_result_serializes_only_structured_score_fields() -> None:
    result = AssessmentResult(
        attempt_id="ATT-1",
        status="unscorable",
        model_version="ta-ctc-1.0.0",
        vocabulary_version="ta-phones-1.0.0",
        scoring_version="gop-1.0.0",
        overall_confidence=0.0,
        reason="alignment_low_confidence",
    )

    payload = result.model_dump(mode="json")

    assert payload["status"] == "unscorable"
    assert set(payload) == {
        "attempt_id",
        "status",
        "model_version",
        "vocabulary_version",
        "scoring_version",
        "phoneme_scores",
        "syllable_scores",
        "overall_confidence",
        "reason",
    }

