"""PHN-002/003: pure, conservative SentencePiece word-span validation."""

import math
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenSpan:
    start: int
    end: int
    score: float


@dataclass(frozen=True)
class AlignedWord:
    text: str
    start: int
    end: int
    score: float


def group_sentencepiece_words(*, tokens, spans):
    if not tokens or len(tokens) != len(spans):
        raise ValueError("invalid token/span count")
    words = []
    pieces = []
    active = []

    def flush():
        if pieces:
            text = unicodedata.normalize("NFC", "".join(pieces)).strip()
            if not text:
                raise ValueError("empty aligned word")
            words.append(
                AlignedWord(
                    text,
                    active[0].start,
                    active[-1].end,
                    sum(s.score for s in active) / len(active),
                )
            )
            pieces.clear()
            active.clear()

    end = -1
    for token, span in zip(tokens, spans, strict=True):
        if (
            span.start < 0
            or span.end <= span.start
            or span.start < end
            or not math.isfinite(span.score)
            or not 0 <= span.score <= 1
        ):
            raise ValueError("invalid aligned token span")
        end = span.end
        if token.startswith("▁"):
            flush()
        if token == "▁":
            continue
        piece = token.removeprefix("▁")
        if not piece or piece in {"<unk>", "<blank>"}:
            raise ValueError("invalid aligned word token")
        pieces.append(piece)
        active.append(span)
    flush()
    if not words:
        raise ValueError("no aligned words")
    return tuple(words)
