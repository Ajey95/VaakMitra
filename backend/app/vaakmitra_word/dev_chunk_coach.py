"""DEC-023/DCH-001..002: transient visual Tamil chunks for adult engineering only."""

from __future__ import annotations

import unicodedata


def _clusters(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", value.strip())
    if not normalized or any(not ("\u0b80" <= char <= "\u0bff") for char in normalized):
        return []
    clusters: list[str] = []
    for char in normalized:
        if unicodedata.category(char).startswith("M"):
            if not clusters:
                return []
            clusters[-1] += char
        elif unicodedata.category(char).startswith("L"):
            clusters.append(char)
        else:
            return []
    return clusters


def build_chunk_coach(target_word: str, candidate_word: str | None, *, capture_valid: bool) -> dict:
    """Return written-chunk rehearsal guidance, never a pronunciation diagnosis."""
    target = unicodedata.normalize("NFC", target_word.strip())
    letters = _clusters(target)
    if not letters:
        return {"status": "visual_only", "target_word": target, "chunks": [],
                "focus_index": None, "focus_position": None, "basis": "manual_visual_practice"}

    block_count = min(3, 1 if len(letters) == 1 else 2 if len(letters) <= 5 else 3)
    base, extra = divmod(len(letters), block_count)
    chunks: list[str] = []
    boundaries: list[range] = []
    start = 0
    for index in range(block_count):
        end = start + base + (1 if index < extra else 0)
        chunks.append("".join(letters[start:end]))
        boundaries.append(range(start, end))
        start = end

    candidate = _clusters(candidate_word) if isinstance(candidate_word, str) else []
    focus_index: int | None = None
    if capture_valid and candidate and candidate != letters:
        mismatch = next((index for index, (expected, observed) in
                         enumerate(zip(letters, candidate)) if expected != observed),
                        min(len(letters), len(candidate)))
        mismatch = min(mismatch, len(letters) - 1)
        focus_index = next(index for index, span in enumerate(boundaries) if mismatch in span)

    return {
        "status": "text_hypothesis" if focus_index is not None else "visual_only",
        "target_word": target,
        "chunks": chunks,
        "focus_index": focus_index,
        "focus_position": ("start" if focus_index == 0 else "end" if focus_index == len(chunks) - 1
                           else "middle") if focus_index is not None else None,
        "basis": "unvalidated_asr_text_difference" if focus_index is not None else "manual_visual_practice",
    }
