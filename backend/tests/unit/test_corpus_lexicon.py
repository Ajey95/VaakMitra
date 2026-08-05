from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from modeling.inventory.consensus import InventorySource
from modeling.inventory.corpus_lexicon import (
    build_corpus_lexicon,
    build_corpus_review_packet,
    write_corpus_review_packet,
    write_private_lexicon,
)

_ARCHIVE_SHA = "a" * 64
_LONG_A = "a\u02d0"


@dataclass
class FakeTransliterator:
    name: str = "fixture"
    version: str = "1.0"

    def transliterate(self, text: str) -> str:
        values = {
            "அம்மா": f"amm{_LONG_A}",
            "தமிழ்": "tamiɻ",
            "நன்று": "nan?u",
        }
        return values[text]


def _private_records(tmp_path: Path) -> tuple[Path, Path]:
    extracted = tmp_path / "extracted"
    transcript_dir = extracted / "mile/train/trans_files"
    transcript_dir.mkdir(parents=True)
    transcripts = (
        ("ISTL_0000001_0000001", "அம்மா, தமிழ்!"),
        ("ISTL_0000002_0000001", "தமிழ் அம்மா அம்மா."),
        ("ISTL_0000003_0000001", "நன்று"),
    )
    records = tmp_path / "records.jsonl"
    rows: list[str] = []
    for utterance_id, transcript in transcripts:
        relative = f"mile/train/trans_files/{utterance_id}.txt"
        path = extracted / relative
        path.write_text(transcript, encoding="utf-8")
        rows.append(
            json.dumps(
                {
                    "utterance_id": utterance_id,
                    "speaker_id": utterance_id.rsplit("_", 1)[0],
                    "audio_sha256": hashlib.sha256(utterance_id.encode()).hexdigest(),
                    "transcript_sha256": hashlib.sha256(transcript.encode()).hexdigest(),
                    "sample_rate_hz": 16000,
                    "duration_ms": 100,
                    "official_split": "train",
                    "audio_rel_path": f"mile/train/audio_files/{utterance_id}.wav",
                    "transcript_rel_path": relative,
                },
                ensure_ascii=False,
            )
        )
    records.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return records, extracted


def _source() -> InventorySource:
    return InventorySource(
        source_id="published",
        revision="b" * 40,
        source_scope="published_inventory",
        segments=("a", _LONG_A, "m", "t", "i", "ɻ"),
    )


def test_corpus_lexicon_streams_unique_words_and_preserves_contrast_units(
    tmp_path: Path,
) -> None:
    records, extracted = _private_records(tmp_path)

    lexicon = build_corpus_lexicon(
        records_path=records,
        extracted_root=extracted,
        archive_sha256=_ARCHIVE_SHA,
        transliterator=FakeTransliterator(),
    )

    assert lexicon.transcript_count == 3
    assert lexicon.word_occurrence_count == 6
    assert tuple(entry.word for entry in lexicon.entries) == ("அம்மா", "தமிழ்")
    amma = lexicon.entries[0]
    assert amma.count == 3
    assert amma.units == ("a", "m", "m", _LONG_A)
    assert lexicon.excluded_unknown_word_count == 1
    assert lexicon.contains_identifiers is False
    assert lexicon.contains_full_transcripts is False


def test_private_record_tampering_and_path_escape_are_rejected(tmp_path: Path) -> None:
    records, extracted = _private_records(tmp_path)
    rows = [json.loads(line) for line in records.read_text(encoding="utf-8").splitlines()]
    rows[0]["transcript_sha256"] = "0" * 64
    records.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    try:
        build_corpus_lexicon(
            records_path=records,
            extracted_root=extracted,
            archive_sha256=_ARCHIVE_SHA,
            transliterator=FakeTransliterator(),
        )
    except ValueError as error:
        assert "digest" in str(error)
    else:
        raise AssertionError("tampered transcript was accepted")

    rows[0]["transcript_rel_path"] = "../../outside.txt"
    records.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    try:
        build_corpus_lexicon(
            records_path=records,
            extracted_root=extracted,
            archive_sha256=_ARCHIVE_SHA,
            transliterator=FakeTransliterator(),
        )
    except ValueError as error:
        assert "path" in str(error)
    else:
        raise AssertionError("escaping transcript path was accepted")


def test_bounded_packet_is_deterministic_and_contains_no_private_identity(
    tmp_path: Path,
) -> None:
    records, extracted = _private_records(tmp_path)
    lexicon = build_corpus_lexicon(
        records_path=records,
        extracted_root=extracted,
        archive_sha256=_ARCHIVE_SHA,
        transliterator=FakeTransliterator(),
    )
    packet = build_corpus_review_packet(
        lexicon=lexicon,
        sources=(_source(),),
        allophones=(),
        version="ta-corpus-candidate-1",
        max_examples=3,
        sample_seed="review-seed-17",
    )
    repeated = build_corpus_review_packet(
        lexicon=lexicon,
        sources=(_source(),),
        allophones=(),
        version="ta-corpus-candidate-1",
        max_examples=3,
        sample_seed="review-seed-17",
    )

    assert packet.digest() == repeated.digest()
    assert len(packet.pronunciation_examples) <= 3
    assert packet.candidate.expert_approved is False
    assert packet.candidate.production_ready is False
    assert packet.unknown_word_count == 1
    assert next(
        item.corpus_frequency for item in packet.token_frequencies if item.token == "m"
    ) == 8

    public_dir = tmp_path / "public"
    private_path = tmp_path / "private/full-lexicon.json"
    write_private_lexicon(private_path, lexicon)
    write_corpus_review_packet(public_dir, packet)

    assert private_path.is_file()
    assert (public_dir / "tamil-phoneme-candidate.json").is_file()
    assert (public_dir / "token-review.csv").is_file()
    assert (public_dir / "pronunciation-review.csv").is_file()
    assert (public_dir / "conflicts-and-coverage.json").is_file()
    assert (public_dir / "approval-manifest.json").is_file()
    with (public_dir / "token-review.csv").open(encoding="utf-8", newline="") as source:
        assert next(csv.reader(source)) == [
            "token",
            "corpus_frequency",
            "source_count",
            "decision",
            "replacement_token",
            "notes",
        ]
    public_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(public_dir.iterdir())
    )
    assert "ISTL_" not in public_text
    assert "audio_files" not in public_text
    assert "trans_files" not in public_text
    assert "அம்மா, தமிழ்!" not in public_text
