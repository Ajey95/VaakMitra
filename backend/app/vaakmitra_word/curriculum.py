"""Registry-backed lesson catalog shared by therapy and assessment adapters."""

from __future__ import annotations

from collections.abc import Sequence

from .vocabulary import VocabularyRegistry


TEACHING_LETTERS: tuple[dict[str, object], ...] = (
    {
        "id": 1,
        "word_id": "TA_00001",
        "type": "letter",
        "symbol": "அ",
        "english": "A",
        "phoneme": "a",
        "image": "/assets/letters/a.png",
        "audio": "/assets/sounds/a.mp3",
        "mouth": "/assets/animations/a_mouth.gif",
        "tip": "Open mouth wide like saying AH",
        "difficulty": 1,
        "scoreable": False,
        "state": "teaching_only",
        "availability_reason": "letters_are_not_word_scoring_targets",
    },
    {
        "id": 2,
        "word_id": "TA_00002",
        "type": "letter",
        "symbol": "ஆ",
        "english": "AA",
        "phoneme": "aa",
        "image": "/assets/letters/aa.png",
        "audio": "/assets/sounds/aa.mp3",
        "mouth": "/assets/animations/aa_mouth.gif",
        "tip": "Hold the AH sound longer — AAAH",
        "difficulty": 1,
        "scoreable": False,
        "state": "teaching_only",
        "availability_reason": "letters_are_not_word_scoring_targets",
    },
    {
        "id": 3,
        "word_id": "TA_00003",
        "type": "letter",
        "symbol": "ல",
        "english": "LA",
        "phoneme": "la",
        "image": "/assets/letters/la.png",
        "audio": "/assets/sounds/la.mp3",
        "mouth": "/assets/animations/la_mouth.gif",
        "tip": "Touch tongue to roof of mouth",
        "difficulty": 2,
        "scoreable": False,
        "state": "teaching_only",
        "availability_reason": "letters_are_not_word_scoring_targets",
    },
    {
        "id": 4,
        "word_id": "TA_00004",
        "type": "letter",
        "symbol": "த",
        "english": "TA",
        "phoneme": "ta",
        "image": "/assets/letters/ta.png",
        "audio": "/assets/sounds/ta.mp3",
        "mouth": "/assets/animations/ta_mouth.gif",
        "tip": "Tap tongue just behind teeth",
        "difficulty": 2,
        "scoreable": False,
        "state": "teaching_only",
        "availability_reason": "letters_are_not_word_scoring_targets",
    },
)

LEGACY_PRONUNCIATIONS = {
    "TA_WORD_0001": "amma",
    "TA_WORD_0002": "appa",
}


def build_lesson_catalog(registry: VocabularyRegistry) -> tuple[dict[str, object], ...]:
    """Build stable numeric routes while retaining stable registry word IDs."""
    lessons = [dict(lesson) for lesson in TEACHING_LETTERS]
    for offset, entry in enumerate(registry.entries, start=len(TEACHING_LETTERS) + 1):
        available = (
            entry.kind == "word"
            and entry.state == "active"
            and entry.scoreable
            and entry.human_review.status == "approved"
        )
        lessons.append(
            {
                "id": offset,
                "word_id": entry.word_id,
                "vocabulary_version": registry.version,
                "type": "word",
                "symbol": entry.canonical_tamil,
                "target_word": entry.canonical_tamil,
                "english": entry.english_gloss,
                "phoneme": LEGACY_PRONUNCIATIONS.get(entry.word_id, entry.canonical_tamil),
                "pronunciation": entry.canonical_tamil,
                "category": entry.category,
                "aliases": list(entry.aliases),
                "tip": f"Listen, then say {entry.canonical_tamil} at a comfortable pace.",
                "difficulty": 2,
                "scoreable": available,
                "state": entry.state,
                "availability_reason": None if available else "word_not_active_and_approved",
            }
        )
    return tuple(lessons)


def lesson_target(
    lessons: Sequence[dict[str, object]],
    lesson_id: int,
    supplied_target: str,
) -> tuple[str, str]:
    """Resolve a server-owned lesson target and reject client label substitution."""
    lesson = next((item for item in lessons if item["id"] == lesson_id), None)
    if lesson is None:
        raise ValueError("lesson and target word do not match")
    target = str(lesson["symbol"])
    accepted = {
        target.casefold(),
        str(lesson.get("phoneme", "")).casefold(),
        *(str(alias).casefold() for alias in lesson.get("aliases", [])),
    }
    if supplied_target.strip().casefold() not in accepted:
        raise ValueError("lesson and target word do not match")
    return str(lesson["word_id"]), target
