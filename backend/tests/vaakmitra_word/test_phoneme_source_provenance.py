"""PHN-002/006: evaluation scope includes upstream origins and audit coverage."""

import pytest
from scripts.model.phoneme_source_provenance import summarize_sources


def row(parent, word, split):
    return {"parent_id": "openslr127:" + parent, "word_id": word, "split": split}


def test_phn006_discloses_source_test_reuse_and_concentrated_partial_audit():
    candidates = [
        {"record": {"utterance_id": p, "official_split": s}}
        for p, s in [("t", "test"), ("a", "train"), ("b", "test")]
    ]
    expansion = {
        "training": [row("t", "w1", "train"), row("t", "w2", "train")],
        "audit": [
            row("a", "w1", "calibration"),
            row("b", "w1", "evaluation"),
            row("b", "w2", "evaluation"),
        ],
    }
    report = summarize_sources(expansion, candidates, {"w1", "w2", "w3"})
    assert report["upstream_official_test_untouched"] is False
    assert report["new_training"]["official_source_clip_counts"] == {"test": 2}
    assert report["new_training"]["official_source_utterance_counts"] == {"test": 1}
    assert report["audit"]["official_source_clip_counts"] == {"train": 1, "test": 2}
    assert report["audit_coverage"]["covered_words"] == 2
    assert report["audit_coverage"]["app_words"] == 3
    assert report["audit_coverage"]["largest_word"] == {"word_id": "w1", "clips": 2}


def test_phn002_source_provenance_rejects_unknown_parent():
    with pytest.raises(ValueError, match="source"):
        summarize_sources(
            {"training": [row("missing", "w", "train")], "audit": []}, [], {"w"}
        )
