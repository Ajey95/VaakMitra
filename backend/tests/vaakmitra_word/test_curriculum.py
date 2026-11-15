"""Dynamic lesson curriculum contracts (DEC-002/003/016, MOD-008)."""

from __future__ import annotations

import pytest

from app.vaakmitra_word.curriculum import build_lesson_catalog, lesson_target
from app.vaakmitra_word.router import VOCABULARY_REGISTRY


def test_dec058_curriculum_contains_teaching_letters_and_all_104_intended_words() -> None:
    lessons = build_lesson_catalog(VOCABULARY_REGISTRY)

    assert len(lessons) == 108
    assert [lesson["type"] for lesson in lessons[:4]] == ["letter"] * 4
    assert all(lesson["scoreable"] is False for lesson in lessons[:4])
    words = lessons[4:]
    assert len(words) == 104
    assert [lesson["word_id"] for lesson in words] == [
        entry.word_id for entry in VOCABULARY_REGISTRY.entries
    ]


def test_intended_but_unapproved_words_are_visible_and_fail_closed() -> None:
    lesson = build_lesson_catalog(VOCABULARY_REGISTRY)[4]

    assert lesson["symbol"] == "அம்மா"
    assert lesson["state"] == "intended"
    assert lesson["scoreable"] is False
    assert lesson["availability_reason"] == "word_not_active_and_approved"


def test_lesson_target_resolves_dynamic_tail_without_hardcoded_ceiling() -> None:
    lessons = build_lesson_catalog(VOCABULARY_REGISTRY)
    last = lessons[-1]

    word_id, target = lesson_target(lessons, last["id"], last["symbol"])

    assert last["id"] == 108
    assert word_id == "TA_WORD_0104"
    assert target == last["symbol"]


def test_lesson_target_rejects_client_supplied_label_mismatch() -> None:
    lessons = build_lesson_catalog(VOCABULARY_REGISTRY)

    with pytest.raises(ValueError, match="lesson and target word do not match"):
        lesson_target(lessons, 5, "அப்பா")
