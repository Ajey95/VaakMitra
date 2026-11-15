"""PHN-002: source split names never override existing speaker isolation."""

import numpy as np
import pytest
from scripts.model.expand_target_words import (
    accept_audio,
    assign_split,
    duration_batches,
    sample_bounds,
    speaker_key,
    validate_cache_headroom,
    validate_segment_record,
    verify_original_prefix,
)


def test_phn002_cache_preflight_reserves_uncompressed_size_and_operating_headroom():
    size = 100 * 48000 * 4 + 128
    with pytest.raises(ValueError, match="space"):
        validate_cache_headroom(size + 1024**3 - 1, 100)
    validate_cache_headroom(size + 1024**3, 100)


def test_phn002_frozen_candidate_roles_and_teacher_quality_cannot_be_rewritten():
    pool = {
        "record": {
            "utterance_id": "u",
            "audio_sha256": "audio",
            "transcript_sha256": "text",
        },
        "speaker": "s",
        "split": "train",
        "wanted_word_ids": ["word"],
        "new_to_student_speaker": False,
    }
    row = {
        "parent_id": "openslr127:u",
        "source_utterance_id": "openslr127:u",
        "speaker": "s",
        "split": "train",
        "word_id": "word",
        "source_audio_sha256": "audio",
        "source_transcript_sha256": "text",
        "teacher_sha256": "teacher",
        "quality_score": 0.95,
        "duration_seconds": 0.5,
        "human_reviewed": False,
        "new_to_student_speaker": False,
        "is_target": True,
    }
    binding = {"teacher_sha256": "teacher", "minimum_alignment_score": 0.85}
    validate_segment_record(row, pool, binding)
    with pytest.raises(ValueError):
        validate_segment_record(dict(row, split="evaluation"), pool, binding)
    with pytest.raises(ValueError):
        validate_segment_record(dict(row, quality_score=float("nan")), pool, binding)


def test_phn002_expanded_cache_compares_only_original_rows_in_last_chunk():
    source = np.arange(6, dtype=np.float32).reshape(3, 2)
    expanded = np.vstack([source, np.ones((2, 2), dtype=np.float32)])
    verify_original_prefix(source, expanded, 2)
    expanded[1, 0] = -1
    with pytest.raises(ValueError):
        verify_original_prefix(source, expanded, 2)


def test_phn002_duration_batches_preserve_every_source_and_bound_padding():
    rows = [{"record": {"duration_ms": n}} for n in [10000, 11000, 1000, 20000]]
    batches = list(duration_batches(rows, 8, 22))
    assert [r for batch in batches for r in batch] == rows
    assert all(
        len(b) * max(r["record"]["duration_ms"] for r in b) / 1000 <= 22
        for b in batches
    )


def test_phn003_word_bounds_and_audio_qa_reject_truncation_noise_and_clipping():
    assert sample_bounds(0, 25, 25, 16000, 16000) == (0, 16000)
    with pytest.raises(ValueError):
        sample_bounds(1, 26, 25, 16000, 16000)
    good = (np.sin(np.arange(4000) * 0.3) * 4000).astype("<i2").tobytes()
    assert accept_audio(good, 16000)
    assert not accept_audio(bytes(8000), 16000)
    assert not accept_audio(np.full(4000, 32767, dtype="<i2").tobytes(), 16000)


def test_phn002_new_sentences_preserve_existing_speaker_roles():
    record = {"speaker_id": "ISTL_0000202", "official_split": "train"}
    assert speaker_key(record) == "openslr127:0000202"
    assert speaker_key({"speaker_id": "MICI_0000202"}) == speaker_key(record)
    assert assign_split(record, {"openslr127:0000202": "evaluation"}) == "evaluation"
    assert assign_split(record, {}) == assign_split(
        dict(record, official_split="test"), {}
    )
