"""Versioned ordered vocabulary for the Tamil phoneme CTC head."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PhonemeVocabulary:
    """Immutable token ordering shared by model, aligner, and scorer."""

    version: str
    tokens: tuple[str, ...]
    blank_token: str = "<blank>"

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("vocabulary version is required")
        if not self.tokens:
            raise ValueError("vocabulary tokens are required")
        if any(not token.strip() for token in self.tokens):
            raise ValueError("vocabulary tokens must be non-empty")
        if len(set(self.tokens)) != len(self.tokens):
            raise ValueError("vocabulary tokens must be unique")
        if self.tokens.count(self.blank_token) != 1:
            raise ValueError("vocabulary must contain exactly one blank token")

    @property
    def blank_index(self) -> int:
        """Return the stable blank index encoded by the ordered vocabulary."""

        return self.tokens.index(self.blank_token)

    def index_of(self, token: str) -> int:
        """Return a token index or an explicit domain error."""

        try:
            return self.tokens.index(token)
        except ValueError as error:
            raise KeyError(f"unknown phoneme token: {token}") from error

    def token_at(self, index: int) -> str:
        """Return the token at a validated vocabulary index."""

        if index < 0 or index >= len(self.tokens):
            raise IndexError(f"phoneme index out of range: {index}")
        return self.tokens[index]

    @classmethod
    def from_json(cls, path: str | Path) -> PhonemeVocabulary:
        """Load the contract fields from a UTF-8 JSON vocabulary file."""

        raw: Any = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("vocabulary JSON must be an object")
        version = raw.get("version")
        blank_token = raw.get("blank_token")
        tokens = raw.get("tokens")
        if not isinstance(version, str) or not isinstance(blank_token, str):
            raise ValueError("vocabulary version and blank_token must be strings")
        if not isinstance(tokens, list) or not all(isinstance(token, str) for token in tokens):
            raise ValueError("vocabulary tokens must be a list of strings")
        return cls(version=version, tokens=tuple(tokens), blank_token=blank_token)
