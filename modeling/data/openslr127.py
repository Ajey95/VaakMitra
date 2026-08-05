"""Private OpenSLR-127 inspection with privacy-safe aggregate evidence."""

from __future__ import annotations

import hashlib
import re
import unicodedata
import wave
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from modeling.data.corpus_index import CorpusRecord, SplitName

OfficialSplit = Literal["train", "test"]
_UTTERANCE_ID = re.compile(r"^(?P<speaker>[A-Za-z]+_[0-9]{7})_[0-9]{7}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PUBLIC_SPLITS: tuple[SplitName, ...] = ("train", "validation", "test")


@dataclass(frozen=True, slots=True)
class MaterializedRecord:
    """Private record; paths, transcript, and identifiers must never be committed."""

    utterance_id: str
    speaker_id: str
    official_split: OfficialSplit
    audio_path: Path
    transcript_path: Path
    normalized_transcript: str
    audio_sha256: str
    transcript_sha256: str
    sample_rate_hz: Literal[16000]
    duration_ms: int

    def corpus_record(self) -> CorpusRecord:
        return CorpusRecord(
            utterance_id=self.utterance_id,
            speaker_id=self.speaker_id,
            audio_sha256=self.audio_sha256,
            transcript_sha256=self.transcript_sha256,
            sample_rate_hz=self.sample_rate_hz,
            duration_ms=self.duration_ms,
        )


class CorpusMaterializationReport(BaseModel):
    """Aggregate inspection result safe for committed engineering evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    dataset_id: Literal["openslr-127-iisc-mile-tamil"] = (
        "openslr-127-iisc-mile-tamil"
    )
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_count: int = Field(ge=0)
    total_duration_ms: int = Field(ge=0)
    official_train_count: int = Field(ge=0)
    official_test_count: int = Field(ge=0)
    accepted_speaker_count: int = Field(ge=0)
    rejections: dict[str, int]
    contains_paths: Literal[False] = False
    contains_transcripts: Literal[False] = False
    contains_identifiers: Literal[False] = False


@dataclass(frozen=True, slots=True)
class CorpusInspectionResult:
    records: tuple[MaterializedRecord, ...]
    report: CorpusMaterializationReport


@dataclass(frozen=True, slots=True)
class SpeakerAssignmentResult:
    assignments: dict[str, SplitName]
    policy_version: str
    official_overlap_count: int

    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
        del mode
        counts = Counter(self.assignments.values())
        return {
            "policy_version": self.policy_version,
            "official_overlap_count": self.official_overlap_count,
            "split_speaker_counts": {
                split: counts.get(split, 0)
                for split in _PUBLIC_SPLITS
            },
            "contains_identifiers": False,
        }


def speaker_from_utterance_id(utterance_id: str) -> str:
    """Extract the corpus speaker component from a validated IISc-MILE identifier."""

    match = _UTTERANCE_ID.fullmatch(utterance_id)
    if match is None:
        raise ValueError("utterance identifier does not expose a validated speaker identity")
    return match.group("speaker")


def _official_split(audio_directory: Path, root: Path) -> OfficialSplit:
    for ancestor in (audio_directory, *audio_directory.parents):
        if ancestor == root.parent:
            break
        normalized = ancestor.name.casefold()
        if normalized == "train":
            return "train"
        if normalized == "test":
            return "test"
    raise ValueError("audio_files directory is not under a train or test partition")


def _tamil_text(path: Path) -> tuple[str | None, str | None]:
    try:
        raw = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None, "invalid_utf8_transcript"
    normalized = unicodedata.normalize("NFC", raw).strip()
    if not normalized:
        return None, "empty_transcript"
    if not any("\u0b80" <= character <= "\u0bff" for character in normalized):
        return None, "non_tamil_transcript"
    return normalized, None


def _audio_metadata(path: Path) -> tuple[int | None, str | None]:
    try:
        with wave.open(str(path), "rb") as source:
            if source.getnchannels() != 1:
                return None, "invalid_wav_channels"
            if source.getframerate() != 16_000:
                return None, "invalid_wav_sample_rate"
            if source.getsampwidth() != 2 or source.getcomptype() != "NONE":
                return None, "invalid_wav_sample_width"
            frame_count = source.getnframes()
    except (EOFError, OSError, wave.Error):
        return None, "invalid_wav_container"
    if frame_count <= 0:
        return None, "invalid_wav_duration"
    duration_ms = round(frame_count * 1000 / 16_000)
    if duration_ms <= 0:
        return None, "invalid_wav_duration"
    return duration_ms, None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_extracted_corpus(
    root: Path, *, archive_sha256: str
) -> CorpusInspectionResult:
    """Pair and validate the complete extracted corpus without public identifiers."""

    if not _SHA256.fullmatch(archive_sha256):
        raise ValueError("archive_sha256 must be a lowercase SHA-256 digest")
    if not root.is_dir():
        raise ValueError("extracted corpus root must be a directory")
    audio_directories = tuple(
        sorted(
            path
            for path in root.rglob("*")
            if path.is_dir() and path.name.casefold() == "audio_files"
        )
    )
    if not audio_directories:
        raise ValueError("no audio_files directories found")

    records: list[MaterializedRecord] = []
    rejections: Counter[str] = Counter()
    for audio_directory in audio_directories:
        try:
            official_split = _official_split(audio_directory, root)
        except ValueError:
            rejections["unknown_official_split"] += sum(
                1 for _ in audio_directory.rglob("*.wav")
            )
            continue
        transcript_directory = audio_directory.parent / "trans_files"
        for audio_path in sorted(audio_directory.rglob("*.wav")):
            relative = audio_path.relative_to(audio_directory).with_suffix(".txt")
            transcript_path = transcript_directory / relative
            if not transcript_path.is_file():
                rejections["missing_transcript"] += 1
                continue
            duration_ms, audio_error = _audio_metadata(audio_path)
            if audio_error is not None:
                rejections[audio_error] += 1
                continue
            transcript, transcript_error = _tamil_text(transcript_path)
            if transcript_error is not None:
                rejections[transcript_error] += 1
                continue
            utterance_id = audio_path.stem
            try:
                speaker_id = speaker_from_utterance_id(utterance_id)
            except ValueError:
                rejections["unrecognized_utterance_id"] += 1
                continue
            assert duration_ms is not None
            assert transcript is not None
            records.append(
                MaterializedRecord(
                    utterance_id=utterance_id,
                    speaker_id=speaker_id,
                    official_split=official_split,
                    audio_path=audio_path,
                    transcript_path=transcript_path,
                    normalized_transcript=transcript,
                    audio_sha256=_file_sha256(audio_path),
                    transcript_sha256=hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
                    sample_rate_hz=16_000,
                    duration_ms=duration_ms,
                )
            )
    ordered = tuple(sorted(records, key=lambda item: item.utterance_id))
    report = CorpusMaterializationReport(
        archive_sha256=archive_sha256,
        accepted_count=len(ordered),
        total_duration_ms=sum(record.duration_ms for record in ordered),
        official_train_count=sum(record.official_split == "train" for record in ordered),
        official_test_count=sum(record.official_split == "test" for record in ordered),
        accepted_speaker_count=len({record.speaker_id for record in ordered}),
        rejections=dict(sorted(rejections.items())),
    )
    return CorpusInspectionResult(records=ordered, report=report)


def _ranked(speakers: set[str], namespace: str) -> list[str]:
    return sorted(
        speakers,
        key=lambda speaker: hashlib.sha256(f"{namespace}:{speaker}".encode()).digest(),
    )


def _validation_count(speaker_count: int) -> int:
    if speaker_count < 2:
        raise ValueError("at least two official training speakers are required")
    return min(speaker_count - 1, max(1, round(speaker_count * 0.10)))


def assign_speakers(
    official_rows: Mapping[str, str] | Sequence[tuple[str, str]],
) -> SpeakerAssignmentResult:
    """Create deterministic speaker-disjoint splits and expose only aggregate evidence."""

    rows = tuple(official_rows.items()) if isinstance(official_rows, Mapping) else tuple(official_rows)
    if not rows:
        raise ValueError("official speaker rows must be non-empty")
    split_speakers: defaultdict[str, set[str]] = defaultdict(set)
    for raw_speaker, raw_split in rows:
        speaker = raw_speaker.strip()
        split = raw_split.strip().casefold()
        if not speaker or split not in {"train", "test"}:
            raise ValueError("official rows require non-empty speakers and train/test splits")
        split_speakers[split].add(speaker)
    train_speakers = split_speakers["train"]
    test_speakers = split_speakers["test"]
    overlap = train_speakers & test_speakers

    assignments: dict[str, SplitName] = {}
    if not overlap:
        if not test_speakers:
            raise ValueError("official test speakers are required")
        validation_count = _validation_count(len(train_speakers))
        validation = set(_ranked(train_speakers, "validation-v1")[:validation_count])
        for speaker in train_speakers:
            assignments[speaker] = "validation" if speaker in validation else "train"
        for speaker in test_speakers:
            assignments[speaker] = "test"
        policy = "official-test-plus-train-validation-sha256-v1"
    else:
        speakers = train_speakers | test_speakers
        if len(speakers) < 3:
            raise ValueError("at least three speakers are required for a full resplit")
        ranked = _ranked(speakers, "full-resplit-v1")
        validation_count = max(1, round(len(ranked) * 0.10))
        test_count = max(1, round(len(ranked) * 0.10))
        if validation_count + test_count >= len(ranked):
            raise ValueError("full resplit must leave at least one training speaker")
        test = set(ranked[:test_count])
        validation = set(ranked[test_count : test_count + validation_count])
        for speaker in speakers:
            if speaker in test:
                assignments[speaker] = "test"
            elif speaker in validation:
                assignments[speaker] = "validation"
            else:
                assignments[speaker] = "train"
        policy = "speaker-sha256-80-10-10-v1"
    return SpeakerAssignmentResult(
        assignments=dict(sorted(assignments.items())),
        policy_version=policy,
        official_overlap_count=len(overlap),
    )
