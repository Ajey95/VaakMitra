"""Vocabulary registry behavior for DEC-003, DEC-016, CLS-001, and DATA-012."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.vaakmitra_word.vocabulary import (
    InactiveVocabularyItem,
    VocabularyEntry,
    VocabularyRegistry,
)


DEFAULT_VOCABULARY = (
    Path(__file__).parents[2] / "data" / "vocabulary" / "ta-v1-intended.json"
)


def test_dec058_intended_v11_contains_104_unique_nfc_tamil_words() -> None:
    """A truncated, duplicated, non-Tamil, or non-NFC release registry must fail."""
    registry = VocabularyRegistry.from_json(DEFAULT_VOCABULARY)

    assert registry.version == "ta-words-v1.1.0"
    assert len(registry.entries) == 104
    assert [entry.word_id for entry in registry.entries] == [f"TA_WORD_{i:04d}" for i in range(1, 105)]
    assert len({entry.word_id for entry in registry.entries}) == 104
    assert len({entry.canonical_tamil for entry in registry.entries}) == 104
    assert all(entry.kind == "word" for entry in registry.entries)
    assert all(entry.state == "intended" for entry in registry.entries)
    assert all(entry.scoreable for entry in registry.entries)
    for entry in registry.entries[-4:]:
        assert entry.human_review.status == "pending"
        with pytest.raises(InactiveVocabularyItem):
            registry.require_active_word(entry.word_id)
    assert all(
        unicodedata.normalize("NFC", entry.canonical_tamil) == entry.canonical_tamil
        for entry in registry.entries
    )
    assert all(any("\u0b80" <= character <= "\u0bff" for character in entry.canonical_tamil)
               for entry in registry.entries)


def test_registry_rejects_duplicate_canonical_words_after_normalization(tmp_path: Path) -> None:
    """Two IDs must not collapse to the same canonical Tamil word."""
    payload = {
        "schema_version": "vaakmitra-vocabulary-1",
        "version": "test-v1",
        "entries": [
            _entry("TA_WORD_0001", "அம்மா"),
            _entry("TA_WORD_0002", unicodedata.normalize("NFD", "அம்மா")),
        ],
    }
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="canonical_tamil must be unique"):
        VocabularyRegistry.from_json(path)


def test_teaching_letter_cannot_be_marked_scoreable() -> None:
    """A future refactor must not reintroduce letter/phoneme correctness scoring."""
    with pytest.raises(ValidationError, match="teaching-only letters cannot be scoreable"):
        VocabularyEntry.model_validate(
            {
                **_entry("TA_LETTER_0001", "அ"),
                "kind": "teaching_letter",
                "scoreable": True,
            }
        )


def test_inactive_word_fails_closed_in_scoreable_lookup() -> None:
    """Missing release evidence must not silently activate an intended word."""
    registry = VocabularyRegistry.model_validate(
        {
            "schema_version": "vaakmitra-vocabulary-1",
            "version": "test-v1",
            "entries": [_entry("TA_WORD_0001", "அம்மா")],
        }
    )

    with pytest.raises(InactiveVocabularyItem, match="TA_WORD_0001"):
        registry.require_active_word("TA_WORD_0001")


def test_active_word_lookup_returns_only_exact_registered_id() -> None:
    """Lookup must not infer a nearest label for an unknown word ID."""
    active = {**_entry("TA_WORD_0001", "அம்மா"), "state": "active"}
    registry = VocabularyRegistry.model_validate(
        {
            "schema_version": "vaakmitra-vocabulary-1",
            "version": "test-v1",
            "entries": [active],
        }
    )

    assert registry.require_active_word("TA_WORD_0001").canonical_tamil == "அம்மா"
    with pytest.raises(InactiveVocabularyItem, match="TA_WORD_9999"):
        registry.require_active_word("TA_WORD_9999")


def _entry(word_id: str, canonical_tamil: str) -> dict[str, object]:
    return {
        "word_id": word_id,
        "canonical_tamil": canonical_tamil,
        "english_gloss": "mother",
        "category": "family_people",
        "aliases": [],
        "kind": "word",
        "state": "intended",
        "scoreable": True,
        "human_review": {"status": "pending", "reviewer_id": None},
    }
