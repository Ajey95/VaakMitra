from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from modeling.inventory.tamil_ipa import generate_inventory, split_ipa_units


@dataclass(frozen=True)
class FakeTransliterator:
    values: dict[str, str]
    name: str = "fixture-transliterator"
    version: str = "1.0"

    def transliterate(self, text: str) -> str:
        return self.values[text]


def test_split_ipa_units_retains_length_combining_marks_and_tie_bars() -> None:
    assert split_ipa_units("a\u02d0m") == ("a\u02d0", "m")
    assert split_ipa_units("n\u032aa") == ("n\u032a", "a")
    assert split_ipa_units("t\u0361\u0283a") == ("t\u0361\u0283", "a")


def test_generated_inventory_is_reproducible_and_unapproved() -> None:
    tamil_word = "\u0b85\u0bae\u0bcd\u0bae\u0bbe"
    transliterator = FakeTransliterator({tamil_word: "amma\u02d0"})

    manifest = generate_inventory((tamil_word,), transliterator, "ta-ipa-proxy-1")
    repeated = generate_inventory((tamil_word,), transliterator, "ta-ipa-proxy-1")

    assert manifest.expert_approved is False
    assert manifest.therapist_approved is False
    assert manifest.lexicon[0].text == tamil_word
    assert manifest.lexicon[0].ipa == "amma\u02d0"
    assert set(manifest.tokens) == {"<blank>", "a", "a\u02d0", "m"}
    assert manifest.digest() == repeated.digest()


def test_generated_inventory_normalizes_tamil_text_to_nfc() -> None:
    decomposed = "\u0b95\u0bc6\u0bbe"
    normalized = "\u0b95\u0bca"
    transliterator = FakeTransliterator({normalized: "ko"})

    manifest = generate_inventory((decomposed,), transliterator, "ta-ipa-proxy-1")

    assert manifest.lexicon[0].text == normalized


@pytest.mark.parametrize(
    ("words", "values", "message"),
    [
        ((), {}, "word list"),
        (("not-tamil",), {"not-tamil": "test"}, "Tamil"),
        (("\u0b85", "\u0b85"), {"\u0b85": "a"}, "duplicate"),
        (("\u0b85",), {"\u0b85": ""}, "empty IPA"),
    ],
)
def test_generated_inventory_rejects_unsafe_inputs(
    words: tuple[str, ...],
    values: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        generate_inventory(words, FakeTransliterator(values), "ta-ipa-proxy-1")


def test_inventory_json_is_utf8_and_json_compatible(tmp_path: Path) -> None:
    tamil_word = "\u0b85\u0bae\u0bcd\u0bae\u0bbe"
    manifest = generate_inventory(
        (tamil_word,),
        FakeTransliterator({tamil_word: "amma\u02d0"}),
        "ta-ipa-proxy-1",
    )
    output = tmp_path / "inventory.json"

    output.write_text(
        json.dumps(manifest.as_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    assert json.loads(output.read_text(encoding="utf-8"))["lexicon"][0]["text"] == tamil_word
