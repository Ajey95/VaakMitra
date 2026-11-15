"""PHN-002/003: whitespace markers are boundaries, not training words."""

import pytest
from scripts.model.target_alignment import TokenSpan, group_sentencepiece_words


def test_phn002_groups_boundary_markers_and_rejects_invalid_spans():
    spans = tuple(TokenSpan(i, i + 1, 0.9) for i in range(5))
    words = group_sentencepiece_words(tokens=("▁", "அம்", "மா", "▁அப்", "பா"), spans=spans)
    assert [w.text for w in words] == ["அம்மா", "அப்பா"]
    assert (words[0].start, words[0].end) == (1, 3)
    with pytest.raises(ValueError):
        group_sentencepiece_words(
            tokens=("▁அம்", "மா"), spans=(TokenSpan(0, 3, 0.9), TokenSpan(2, 4, 0.9))
        )
    with pytest.raises(ValueError):
        group_sentencepiece_words(tokens=("▁",), spans=(TokenSpan(0, 1, 0.9),))
