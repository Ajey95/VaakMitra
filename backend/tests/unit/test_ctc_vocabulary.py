from __future__ import annotations

import json

import pytest

from vaakmitra.ctc.vocabulary import PhonemeVocabulary


def test_vocabulary_requires_exactly_one_blank() -> None:
    with pytest.raises(ValueError, match="blank"):
        PhonemeVocabulary(version="v1", tokens=("a", "m"), blank_token="<blank>")


def test_vocabulary_rejects_duplicate_tokens() -> None:
    with pytest.raises(ValueError, match="unique"):
        PhonemeVocabulary(
            version="v1",
            tokens=("<blank>", "a", "a"),
            blank_token="<blank>",
        )


def test_vocabulary_exposes_stable_indices() -> None:
    vocabulary = PhonemeVocabulary(
        version="ta-fixture-1.0.0",
        tokens=("<blank>", "a", "m", "a:"),
        blank_token="<blank>",
    )

    assert vocabulary.blank_index == 0
    assert vocabulary.index_of("m") == 2
    assert vocabulary.token_at(3) == "a:"
    with pytest.raises(KeyError, match="unknown phoneme"):
        vocabulary.index_of("z")


def test_vocabulary_loads_versioned_json(tmp_path) -> None:
    path = tmp_path / "vocabulary.json"
    path.write_text(
        json.dumps(
            {
                "version": "ta-fixture-1.0.0",
                "blank_token": "<blank>",
                "tokens": ["<blank>", "a", "m", "a:"],
            }
        ),
        encoding="utf-8",
    )

    vocabulary = PhonemeVocabulary.from_json(path)

    assert vocabulary.version == "ta-fixture-1.0.0"
    assert vocabulary.tokens == ("<blank>", "a", "m", "a:")

