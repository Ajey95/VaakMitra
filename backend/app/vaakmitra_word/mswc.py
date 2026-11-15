"""MLCommons Multilingual Spoken Words manifest conversion for Tamil OTHER data."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath

from scipy.io import wavfile

from .corpus import CorpusManifestError, CorpusRecord, SourceEntry
from .corpus_preprocessing import assign_speaker_split


def _duration_seconds(path: Path) -> float:
    if path.suffix.casefold() == ".wav":
        sample_rate, samples = wavfile.read(path, mmap=True)
        return len(samples) / float(sample_rate)
    completed = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise CorpusManifestError(f"audio_duration_unavailable:{path.name}")
    try:
        duration = float(completed.stdout.strip())
    except ValueError as exc:
        raise CorpusManifestError(f"audio_duration_invalid:{path.name}") from exc
    if duration <= 0:
        raise CorpusManifestError(f"audio_duration_invalid:{path.name}")
    return duration


def _resolve_audio(root: Path, link: str) -> tuple[Path, str]:
    relative = PurePosixPath(link)
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) < 2:
        raise CorpusManifestError("mswc_link_invalid")
    candidates = (
        root.joinpath(*relative.parts),
        root / f"{relative.parts[-2]}_{relative.name}",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate, candidate.relative_to(root).as_posix()
    raise CorpusManifestError(f"audio_unavailable:{link}")


def build_mswc_manifest(
    csv_paths: tuple[Path, ...] | list[Path],
    *,
    audio_root: Path | str,
    output_path: Path | str,
    source: SourceEntry,
    seed: int,
) -> int:
    if not source.enabled or source.licence_status != "verified" or "other" not in source.intended_uses:
        raise CorpusManifestError("mswc_source_not_approved_for_other")
    destination = Path(output_path)
    if destination.exists():
        raise FileExistsError(destination)
    rows: list[dict[str, str]] = []
    for csv_path in csv_paths:
        with Path(csv_path).open("r", encoding="utf-8", newline="") as source_file:
            for row in csv.DictReader(source_file):
                if row.get("VALID", "").casefold() == "true":
                    rows.append({key: value or "" for key, value in row.items()})
    rows.sort(key=lambda row: (row["LINK"], row["SPEAKER"]))
    if len({row["LINK"] for row in rows}) != len(rows):
        raise CorpusManifestError("mswc_link_duplicate")

    root = Path(audio_root).resolve()
    records: list[CorpusRecord] = []
    for row in rows:
        audio_path, relative_audio = _resolve_audio(root, row["LINK"])
        speaker = hashlib.sha256(
            f"{source.source_id}:{row['SPEAKER']}".encode("utf-8")
        ).hexdigest()[:24]
        original_id = row["LINK"]
        records.append(
            CorpusRecord(
                schema_version="vaakmitra-corpus-record-1",
                sample_id=f"mswc-ta-{hashlib.sha256(original_id.encode('utf-8')).hexdigest()[:24]}",
                source_id=source.source_id,
                source_revision=source.source_revision,
                original_id=original_id,
                speaker_pseudonym=f"mswc-{speaker}",
                canonical_word_id=None,
                label_kind="other",
                transcript=row["WORD"],
                audio_path=relative_audio,
                audio_sha256=hashlib.sha256(audio_path.read_bytes()).hexdigest(),
                duration_seconds=_duration_seconds(audio_path),
                split=assign_speaker_split(f"mswc-{speaker}", seed=seed),
                licence_id=source.licence_id,
            )
        )
    if not records:
        raise CorpusManifestError("mswc_manifest_empty")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as sink:
        for record in records:
            sink.write(record.model_dump_json() + "\n")
    return len(records)
