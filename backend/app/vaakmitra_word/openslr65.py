"""Governed sentence-level OpenSLR 65 manifest generation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from scipy.io import wavfile

from .corpus import CorpusManifestError, CorpusRecord, SourceEntry
from .corpus_preprocessing import assign_speaker_split


@dataclass(frozen=True)
class OpenSlr65Partition:
    index_path: Path
    audio_root: Path


def _speaker(file_id: str) -> str:
    parts = file_id.split("_")
    if len(parts) < 3 or not parts[0] or not parts[1]:
        raise CorpusManifestError(f"openslr65_file_id_invalid:{file_id}")
    return f"{parts[0]}_{parts[1]}"


def build_openslr65_manifest(
    partitions: tuple[OpenSlr65Partition, ...] | list[OpenSlr65Partition],
    *,
    corpus_root: Path | str,
    output_path: Path | str,
    source: SourceEntry,
    seed: int,
) -> int:
    if not source.enabled or source.licence_status != "verified" or "other" not in source.intended_uses:
        raise CorpusManifestError("openslr65_source_not_approved")
    destination = Path(output_path)
    if destination.exists():
        raise FileExistsError(destination)
    root = Path(corpus_root).resolve()
    rows: list[tuple[str, str | None, Path]] = []
    for partition in partitions:
        audio_root = partition.audio_root.resolve()
        try:
            audio_root.relative_to(root)
        except ValueError as exc:
            raise CorpusManifestError("openslr65_audio_root_outside_corpus") from exc
        with partition.index_path.open("r", encoding="utf-8") as index:
            for line_number, line in enumerate(index, start=1):
                if not line.strip():
                    continue
                file_id, separator, transcript = line.rstrip("\r\n").partition("\t")
                if not separator:
                    raise CorpusManifestError(f"openslr65_index_invalid:{line_number}")
                normalized_transcript = transcript.strip() or None
                rows.append((file_id, normalized_transcript, audio_root))
    rows.sort(key=lambda item: item[0])
    if not rows or len({file_id for file_id, _, _ in rows}) != len(rows):
        raise CorpusManifestError("openslr65_ids_empty_or_duplicate")

    records: list[CorpusRecord] = []
    for file_id, transcript, audio_root in rows:
        audio_path = audio_root / f"{file_id}.wav"
        if not audio_path.is_file():
            raise CorpusManifestError(f"audio_unavailable:{file_id}")
        sample_rate, samples = wavfile.read(audio_path, mmap=True)
        duration = len(samples) / float(sample_rate)
        speaker = _speaker(file_id)
        speaker_pseudonym = "slr65-" + hashlib.sha256(
            f"{source.source_id}:{speaker}".encode("utf-8")
        ).hexdigest()[:24]
        records.append(
            CorpusRecord(
                schema_version="vaakmitra-corpus-record-1",
                sample_id=f"slr65-{file_id}",
                source_id=source.source_id,
                source_revision=source.source_revision,
                original_id=file_id,
                speaker_pseudonym=speaker_pseudonym,
                canonical_word_id=None,
                label_kind="other",
                transcript=transcript,
                audio_path=audio_path.relative_to(root).as_posix(),
                audio_sha256=hashlib.sha256(audio_path.read_bytes()).hexdigest(),
                duration_seconds=duration,
                split=assign_speaker_split(speaker_pseudonym, seed=seed),
                licence_id=source.licence_id,
            )
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as sink:
        for record in records:
            sink.write(record.model_dump_json() + "\n")
    return len(records)
