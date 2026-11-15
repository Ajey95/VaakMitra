"""Versioned Tamil whole-word registry (DEC-003, DEC-016, CLS-001, DATA-012)."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InactiveVocabularyItem(LookupError):
    """Raised when a requested word is absent or not active for scoring."""


class HumanReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["pending", "approved", "rejected"] = "pending"
    reviewer_id: str | None = None

    @model_validator(mode="after")
    def require_reviewer_for_decision(self) -> "HumanReview":
        if self.status != "pending" and not self.reviewer_id:
            raise ValueError("reviewer_id is required for a completed human review")
        return self


class VocabularyEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    word_id: str = Field(pattern=r"^TA_(?:WORD|LETTER)_\d{4}$")
    canonical_tamil: str = Field(min_length=1)
    english_gloss: str = Field(min_length=1)
    category: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    kind: Literal["word", "teaching_letter"] = "word"
    state: Literal["candidate", "intended", "active", "disabled"] = "candidate"
    scoreable: bool = True
    human_review: HumanReview = Field(default_factory=HumanReview)

    @field_validator("canonical_tamil")
    @classmethod
    def canonicalize_tamil(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFC", value).strip()
        if normalized != value:
            raise ValueError("canonical_tamil must already be trimmed NFC text")
        if not any("\u0b80" <= character <= "\u0bff" for character in normalized):
            raise ValueError("canonical_tamil must contain Tamil characters")
        return normalized

    @field_validator("aliases")
    @classmethod
    def normalize_aliases(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(unicodedata.normalize("NFC", value).strip() for value in values)
        if any(not value for value in normalized) or len(set(normalized)) != len(normalized):
            raise ValueError("aliases must be non-empty and unique")
        return normalized

    @model_validator(mode="after")
    def enforce_word_only_scoring(self) -> "VocabularyEntry":
        if self.kind == "teaching_letter" and self.scoreable:
            raise ValueError("teaching-only letters cannot be scoreable")
        if self.kind == "word" and not self.word_id.startswith("TA_WORD_"):
            raise ValueError("word entries require TA_WORD identifiers")
        if self.kind == "teaching_letter" and not self.word_id.startswith("TA_LETTER_"):
            raise ValueError("teaching letters require TA_LETTER identifiers")
        return self


class VocabularyRegistry(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["vaakmitra-vocabulary-1"]
    version: str = Field(min_length=1)
    entries: tuple[VocabularyEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_uniqueness(self) -> "VocabularyRegistry":
        word_ids = [entry.word_id for entry in self.entries]
        if len(set(word_ids)) != len(word_ids):
            raise ValueError("word_id must be unique")
        canonical_words = [entry.canonical_tamil for entry in self.entries]
        if len(set(canonical_words)) != len(canonical_words):
            raise ValueError("canonical_tamil must be unique")
        return self

    @classmethod
    def from_json(cls, path: Path | str) -> "VocabularyRegistry":
        with Path(path).open("r", encoding="utf-8") as source:
            return cls.model_validate(json.load(source))

    def require_active_word(self, word_id: str) -> VocabularyEntry:
        for entry in self.entries:
            if (
                entry.word_id == word_id
                and entry.kind == "word"
                and entry.scoreable
                and entry.state == "active"
            ):
                return entry
        raise InactiveVocabularyItem(word_id)
