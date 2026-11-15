"""DEC-016 / Section 13.1: assigned words come from the versioned registry."""

import pytest
from pydantic import ValidationError

from app.routers.therapist_ext import PlanCreate


def test_dec016_plan_accepts_versioned_whole_words() -> None:
    plan = PlanCreate(child_id="child-1", title="First words", word_ids=["TA_WORD_0001", "TA_WORD_0002"],
                      vocabulary_version="ta-words-v1.1.0")
    assert plan.word_ids == ["TA_WORD_0001", "TA_WORD_0002"]


@pytest.mark.parametrize("words,version", [
    (["TA_WORD_0001", "TA_WORD_0001"], "ta-words-v1.1.0"),
    (["TA_WORD_9999"], "ta-words-v1.1.0"),
    (["TA_LETTER_0001"], "ta-words-v1.1.0"),
    (["TA_WORD_0001"], "wrong-version"),
    (["TA_WORD_0001"], "ta-words-v1.0.0"), # DEC-058: stale plans need an explicit current registry version.
    (["TA_WORD_0001"], None),
])
def test_dec016_plan_rejects_unassigned_or_mismatched_vocabulary(words, version) -> None:
    with pytest.raises(ValidationError):
        PlanCreate(child_id="child-1", title="First words", word_ids=words, vocabulary_version=version)
