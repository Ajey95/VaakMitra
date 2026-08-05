"""Generate a reproducible provisional Tamil IPA inventory without approval claims."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import unicodedata
from collections.abc import Sequence
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

_LENGTH_MARKS = frozenset({"\u02d0", "\u02d1"})
_TIE_BARS = frozenset({"\u035c", "\u0361"})
_TAMIL_START = 0x0B80
_TAMIL_END = 0x0BFF


class Transliterator(Protocol):
    """Small injection boundary implemented by Epitran or deterministic fixtures."""

    name: str
    version: str

    def transliterate(self, text: str) -> str: ...


class LexiconEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1)
    ipa: str = Field(min_length=1)
    units: tuple[str, ...] = Field(min_length=1)


class InventoryManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    inventory_version: str = Field(min_length=1)
    generator: str = Field(min_length=1)
    generator_version: str = Field(min_length=1)
    source_words_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    blank_token: Literal["<blank>"] = "<blank>"
    tokens: tuple[str, ...] = Field(min_length=2)
    lexicon: tuple[LexiconEntry, ...] = Field(min_length=1)
    expert_approved: Literal[False] = False
    therapist_approved: Literal[False] = False
    evidence_scope: Literal["provisional_research_inventory"] = (
        "provisional_research_inventory"
    )

    def digest(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["inventory_digest"] = self.digest()
        return payload


class EpitranTamilTransliterator:
    """Optional Epitran adapter kept outside the production Member 1 path."""

    name = "epitran"

    def __init__(self, *, reduced: bool = False) -> None:
        try:
            epitran = importlib.import_module("epitran")
            self.version = importlib.metadata.version("epitran")
        except (ImportError, importlib.metadata.PackageNotFoundError) as error:
            raise RuntimeError("epitran optional dependency is not installed") from error
        code = "tam-Taml-red" if reduced else "tam-Taml"
        try:
            self._engine = epitran.Epitran(code)
        except UnicodeDecodeError as error:
            raise RuntimeError(
                "Epitran/PanPhon requires Python UTF-8 mode on this Windows locale; "
                "set PYTHONUTF8=1 before starting Python"
            ) from error

    def transliterate(self, text: str) -> str:
        return str(self._engine.transliterate(text))


def split_ipa_units(ipa: str) -> tuple[str, ...]:
    """Split IPA bases while retaining combining marks, length, and tied affricates."""

    normalized = unicodedata.normalize("NFC", ipa.strip())
    if not normalized:
        raise ValueError("empty IPA transcription")
    units: list[str] = []
    join_next_base = False
    for character in normalized:
        if character.isspace():
            join_next_base = False
            continue
        if unicodedata.combining(character) or character in _LENGTH_MARKS:
            if not units:
                raise ValueError("IPA modifier requires a preceding base unit")
            units[-1] += character
            if character in _TIE_BARS:
                join_next_base = True
            continue
        if join_next_base:
            units[-1] += character
            join_next_base = False
        else:
            units.append(character)
    if join_next_base or not units:
        raise ValueError("IPA transcription ends with an incomplete unit")
    return tuple(units)


def _is_tamil_text(text: str) -> bool:
    return any(_TAMIL_START <= ord(character) <= _TAMIL_END for character in text)


def _source_digest(words: Sequence[str]) -> str:
    canonical = json.dumps(
        list(words),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def generate_inventory(
    words: Sequence[str],
    transliterator: Transliterator,
    version: str,
) -> InventoryManifest:
    """Generate a deterministic unapproved inventory from a Tamil word list."""

    if not words:
        raise ValueError("word list must be non-empty")
    if not version.strip():
        raise ValueError("inventory version must be non-empty")
    normalized_words = tuple(unicodedata.normalize("NFC", word.strip()) for word in words)
    if any(not word for word in normalized_words):
        raise ValueError("word list entries must be non-empty")
    if any(not _is_tamil_text(word) for word in normalized_words):
        raise ValueError("word list entries must contain Tamil text")
    if len(normalized_words) != len(set(normalized_words)):
        raise ValueError("duplicate normalized Tamil word")

    lexicon: list[LexiconEntry] = []
    inventory_units: set[str] = set()
    for word in normalized_words:
        ipa = unicodedata.normalize("NFC", transliterator.transliterate(word).strip())
        if not ipa:
            raise ValueError("empty IPA transcription")
        units = split_ipa_units(ipa)
        if "<blank>" in units:
            raise ValueError("IPA units cannot collide with the blank token")
        inventory_units.update(units)
        lexicon.append(LexiconEntry(text=word, ipa=ipa, units=units))

    return InventoryManifest(
        inventory_version=version.strip(),
        generator=transliterator.name,
        generator_version=transliterator.version,
        source_words_sha256=_source_digest(normalized_words),
        tokens=("<blank>", *sorted(inventory_units)),
        lexicon=tuple(lexicon),
    )
