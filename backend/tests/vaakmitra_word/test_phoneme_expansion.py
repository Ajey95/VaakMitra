"""PHN-001/002: expansion cannot reassign old data or leak held-out speakers."""

import pytest
from scripts.model.prepare_phoneme_expansion import (
    parent,
    source_utterance_id,
    validate_expansion_rows,
)


def test_phn002_source_utterances_are_not_word_crops_or_split_paths():
    assert source_utterance_id(
        {"original_id": "word1/common_voice_ta_123.opus"}
    ) == source_utterance_id({"original_id": "word1/common_voice_ta_123__2.opus"})
    assert source_utterance_id(
        {"original_id": "word1/common_voice_ta_123.opus"}
    ) == source_utterance_id({"original_id": "word2/common_voice_ta_123.opus"})
    assert parent({"audio_path": "train/ISTL_123/01.wav"}) == parent(
        {"audio_path": "evaluation/ISTL_123/02.wav"}
    )
    base = [{"split": "train", "speaker": "a", "audio_sha256": "a", "parent_id": "old"}]
    fresh = {"split": "train", "speaker": "b", "audio_sha256": "b", "parent_id": "same"}
    audit = {
        "split": "evaluation",
        "speaker": "c",
        "audio_sha256": "c",
        "parent_id": "same",
    }
    with pytest.raises(ValueError, match="parent"):
        validate_expansion_rows(base, base + [fresh], [audit])


def test_phn002_new_training_never_uses_heldout_speaker_parent_or_duplicate():
    base = [
        {"split": "train", "speaker": "a", "audio_sha256": "a", "parent_id": "pa"},
        {"split": "evaluation", "speaker": "b", "audio_sha256": "b", "parent_id": "pb"},
    ]
    fresh = {"split": "train", "speaker": "c", "audio_sha256": "c", "parent_id": "pc"}
    validate_expansion_rows(base, base + [fresh])
    for bad in [
        dict(fresh, speaker="b"),
        dict(fresh, parent_id="pb"),
        dict(fresh, audio_sha256="a"),
        dict(fresh, split="evaluation"),
    ]:
        with pytest.raises(ValueError):
            validate_expansion_rows(base, base + [bad])
    with pytest.raises(ValueError):
        validate_expansion_rows(base, list(reversed(base)) + [fresh])
