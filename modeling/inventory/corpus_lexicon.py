"""Build a private Tamil corpus lexicon and a bounded public expert-review packet."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from modeling.inventory.clinician_review import create_review_template
from modeling.inventory.consensus import (
    AllophoneRule,
    CandidateInventory,
    InventorySource,
    build_candidate_inventory,
)
from modeling.inventory.tamil_ipa import Transliterator, split_ipa_units

_TAMIL_WORD = re.compile(r"[\u0b80-\u0bff]+")
_UNKNOWN_UNITS = frozenset({"?", "�", "<unk>", "<UNK>"})


def _canonical_digest(payload: object) -> str:
    canonical = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class CorpusLexiconEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    word: str = Field(min_length=1)
    count: int = Field(gt=0)
    ipa: str = Field(min_length=1)
    units: tuple[str, ...] = Field(min_length=1)


class CorpusLexicon(BaseModel):
    """Sensitive word-level lexicon; it must remain in the ignored artifact boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    private_index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator: str = Field(min_length=1)
    generator_version: str = Field(min_length=1)
    transcript_count: int = Field(gt=0)
    word_occurrence_count: int = Field(gt=0)
    entries: tuple[CorpusLexiconEntry, ...] = Field(min_length=1)
    excluded_unknown_word_count: int = Field(ge=0)
    contains_identifiers: Literal[False] = False
    contains_full_transcripts: Literal[False] = False
    contains_audio_paths: Literal[False] = False

    def digest(self) -> str:
        return _canonical_digest(self.model_dump(mode="json"))


class TokenFrequency(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str
    corpus_frequency: int = Field(ge=0)
    source_count: int = Field(ge=0)


class PronunciationExample(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    example_id: str = Field(pattern=r"^example-[0-9]{4}$")
    word: str
    ipa: str
    units: tuple[str, ...]
    token_focus: str
    corpus_word_frequency: int = Field(gt=0)


class CorpusReviewPacket(BaseModel):
    """Bounded public evidence: isolated words only, never transcripts or identities."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lexicon_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    sample_seed: str = Field(min_length=1)
    candidate: CandidateInventory
    token_frequencies: tuple[TokenFrequency, ...]
    pronunciation_examples: tuple[PronunciationExample, ...]
    unknown_word_count: int = Field(ge=0)
    contains_identifiers: Literal[False] = False
    contains_full_transcripts: Literal[False] = False
    contains_paths: Literal[False] = False

    def digest(self) -> str:
        return _canonical_digest(self.model_dump(mode="json"))


def _safe_transcript_path(root: Path, relative_value: object) -> Path:
    if not isinstance(relative_value, str) or not relative_value:
        raise ValueError("private record transcript path is invalid")
    root_resolved = root.resolve()
    candidate = (root_resolved / Path(relative_value)).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as error:
        raise ValueError("private record transcript path escapes extracted root") from error
    if not candidate.is_file():
        raise ValueError("private record transcript path is missing")
    return candidate


def _words(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFC", text).strip()
    return tuple(_TAMIL_WORD.findall(normalized))


def build_corpus_lexicon(
    *,
    records_path: Path,
    extracted_root: Path,
    archive_sha256: str,
    transliterator: Transliterator,
) -> CorpusLexicon:
    """Stream private records, verify transcript digests, and derive a unique-word lexicon."""

    if not re.fullmatch(r"[0-9a-f]{64}", archive_sha256):
        raise ValueError("archive_sha256 must be a lowercase SHA-256 digest")
    if not records_path.is_file():
        raise ValueError("private records JSONL is missing")
    index_digest = hashlib.sha256()
    counts: Counter[str] = Counter()
    transcript_count = 0
    with records_path.open("rb") as binary_source:
        for block in iter(lambda: binary_source.read(1024 * 1024), b""):
            index_digest.update(block)
    with records_path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            payload: Any = json.loads(line)
            if not isinstance(payload, dict):
                raise TypeError(f"private record line {line_number} is not an object")
            path = _safe_transcript_path(extracted_root, payload.get("transcript_rel_path"))
            normalized = unicodedata.normalize("NFC", path.read_text(encoding="utf-8")).strip()
            declared_digest = payload.get("transcript_sha256")
            actual_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            if declared_digest != actual_digest:
                raise ValueError(f"transcript digest mismatch on private record line {line_number}")
            transcript_words = _words(normalized)
            if not transcript_words:
                raise ValueError(f"no Tamil words on private record line {line_number}")
            counts.update(transcript_words)
            transcript_count += 1
    if transcript_count == 0 or not counts:
        raise ValueError("private records contain no usable Tamil transcripts")

    entries: list[CorpusLexiconEntry] = []
    unknown_count = 0
    for word in sorted(counts):
        ipa = unicodedata.normalize("NFC", transliterator.transliterate(word).strip())
        if not ipa:
            raise ValueError("transliterator returned an empty pronunciation")
        units = split_ipa_units(ipa)
        if any(unit in _UNKNOWN_UNITS for unit in units):
            unknown_count += 1
            continue
        entries.append(
            CorpusLexiconEntry(word=word, count=counts[word], ipa=ipa, units=units)
        )
    if not entries:
        raise ValueError("every corpus word produced an unknown pronunciation")
    return CorpusLexicon(
        archive_sha256=archive_sha256,
        private_index_sha256=index_digest.hexdigest(),
        generator=transliterator.name,
        generator_version=transliterator.version,
        transcript_count=transcript_count,
        word_occurrence_count=sum(counts.values()),
        entries=tuple(entries),
        excluded_unknown_word_count=unknown_count,
    )


def build_corpus_review_packet(
    *,
    lexicon: CorpusLexicon,
    sources: Sequence[InventorySource],
    allophones: Sequence[AllophoneRule],
    version: str,
    max_examples: int,
    sample_seed: str,
) -> CorpusReviewPacket:
    """Create a deterministic candidate plus a bounded, identity-free review sample."""

    if max_examples <= 0:
        raise ValueError("max_examples must be positive")
    if not sample_seed.strip():
        raise ValueError("sample_seed must be non-empty")
    corpus_frequency: Counter[str] = Counter()
    observed: list[str] = []
    for entry in lexicon.entries:
        observed.extend(entry.units)
        for unit in entry.units:
            corpus_frequency[unit] += entry.count
    corpus_source = InventorySource(
        source_id="openslr-127-corpus-observation",
        revision=lexicon.digest(),
        source_scope="corpus_observation",
        segments=tuple(sorted(set(observed))),
    )
    candidate = build_candidate_inventory(
        sources=(*sources, corpus_source),
        observed_units=observed,
        allophones=allophones,
        version=version,
    )
    frequencies = tuple(
        TokenFrequency(
            token=provenance.token,
            corpus_frequency=corpus_frequency[provenance.token],
            source_count=len(provenance.source_ids),
        )
        for provenance in candidate.token_provenance
    )
    sample_candidates = [
        (unit, entry)
        for entry in lexicon.entries
        for unit in sorted(set(entry.units))
    ]
    sample_candidates.sort(
        key=lambda pair: (
            hashlib.sha256(
                f"{sample_seed}|{pair[0]}|{pair[1].word}".encode()
            ).hexdigest(),
            pair[0],
            pair[1].word,
        )
    )
    selected = sample_candidates[:max_examples]
    examples = tuple(
        PronunciationExample(
            example_id=f"example-{index:04d}",
            word=entry.word,
            ipa=entry.ipa,
            units=entry.units,
            token_focus=unit,
            corpus_word_frequency=entry.count,
        )
        for index, (unit, entry) in enumerate(selected, start=1)
    )
    return CorpusReviewPacket(
        archive_sha256=lexicon.archive_sha256,
        lexicon_digest=lexicon.digest(),
        sample_seed=sample_seed,
        candidate=candidate,
        token_frequencies=frequencies,
        pronunciation_examples=examples,
        unknown_word_count=lexicon.excluded_unknown_word_count,
    )


def _write_json(path: Path, payload: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")


def write_private_lexicon(path: Path, lexicon: CorpusLexicon) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, {**lexicon.model_dump(mode="json"), "lexicon_digest": lexicon.digest()})


def write_corpus_review_packet(output_dir: Path, packet: CorpusReviewPacket) -> None:
    """Write stable review artifacts, refusing to mix with an existing output directory."""

    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("review packet output directory must be empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "tamil-phoneme-candidate.json", packet.candidate.as_dict())
    with (output_dir / "token-review.csv").open(
        "x", encoding="utf-8", newline=""
    ) as output:
        writer = csv.writer(output)
        writer.writerow(
            ("token", "corpus_frequency", "source_count", "decision", "replacement_token", "notes")
        )
        for item in packet.token_frequencies:
            writer.writerow((item.token, item.corpus_frequency, item.source_count, "pending", "", ""))
    with (output_dir / "pronunciation-review.csv").open(
        "x", encoding="utf-8", newline=""
    ) as output:
        writer = csv.writer(output)
        writer.writerow(
            (
                "example_id",
                "word",
                "ipa",
                "units",
                "token_focus",
                "corpus_word_frequency",
                "decision",
                "corrected_ipa",
                "notes",
            )
        )
        for example in packet.pronunciation_examples:
            writer.writerow(
                (
                    example.example_id,
                    example.word,
                    example.ipa,
                    " ".join(example.units),
                    example.token_focus,
                    example.corpus_word_frequency,
                    "pending",
                    "",
                    "",
                )
            )
    _write_json(
        output_dir / "conflicts-and-coverage.json",
        {
            "schema_version": "1.0",
            "archive_sha256": packet.archive_sha256,
            "lexicon_digest": packet.lexicon_digest,
            "candidate_digest": packet.candidate.digest(),
            "packet_digest": packet.digest(),
            "conflicts": [item.model_dump(mode="json") for item in packet.candidate.conflicts],
            "unknown_word_count": packet.unknown_word_count,
            "bounded_pronunciation_example_count": len(packet.pronunciation_examples),
            "contains_identifiers": False,
            "contains_full_transcripts": False,
            "contains_paths": False,
            "review_status": "pending_expert_review",
        },
    )
    _write_json(
        output_dir / "approval-manifest.json",
        create_review_template(packet.candidate).model_dump(mode="json"),
    )
