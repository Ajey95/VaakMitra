"""Deterministic audio preparation and deduplication for adult corpora."""

from __future__ import annotations

import hashlib
import json
import subprocess
import unicodedata
from collections import Counter
from dataclasses import dataclass
from math import gcd
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

import numpy as np
from pydantic import ValidationError
from scipy.io import wavfile
from scipy.signal import resample_poly

from .corpus import CorpusRecord
from .vocabulary import VocabularyRegistry


class PreprocessingRejection(ValueError):
    """An input failed a deterministic corpus quality gate."""


@dataclass(frozen=True)
class AudioPolicy:
    target_sample_rate: int = 16_000
    min_duration_seconds: float = 0.30
    max_duration_seconds: float = 12.0
    min_speech_seconds: float = 0.20
    min_rms: float = 0.005
    clipping_amplitude: float = 0.999
    max_clipping_ratio: float = 0.01
    near_duplicate_similarity: float = 0.995

    def __post_init__(self) -> None:
        if self.target_sample_rate <= 0:
            raise ValueError("target sample rate must be positive")
        if not 0 < self.min_duration_seconds < self.max_duration_seconds:
            raise ValueError("duration limits must be positive and ordered")
        if not 0 < self.min_speech_seconds <= self.max_duration_seconds:
            raise ValueError("speech duration limit is invalid")
        if not 0 <= self.max_clipping_ratio <= 1:
            raise ValueError("clipping ratio must be in [0, 1]")
        if not 0 < self.near_duplicate_similarity <= 1:
            raise ValueError("near duplicate similarity must be in (0, 1]")


@dataclass(frozen=True)
class PreparedAudio:
    samples: np.ndarray
    sample_rate: int
    duration_seconds: float
    speech_seconds: float
    rms: float
    peak: float
    clipping_ratio: float
    pcm_sha256: str
    fingerprint: np.ndarray


@dataclass(frozen=True)
class PreprocessingReport:
    accepted: int
    rejected: int
    rejection_counts: dict[str, int]
    manifest_path: Path


def _float_mono(samples: np.ndarray) -> np.ndarray:
    raw = np.asarray(samples)
    if raw.ndim not in (1, 2) or raw.size == 0:
        raise PreprocessingRejection("invalid_audio:expected_non_empty_mono_or_channels")
    if np.issubdtype(raw.dtype, np.integer):
        limit = max(abs(np.iinfo(raw.dtype).min), np.iinfo(raw.dtype).max)
        value = raw.astype(np.float64) / float(limit)
    else:
        value = raw.astype(np.float64)
    if value.ndim == 2:
        value = value.mean(axis=1)
    if not np.isfinite(value).all():
        raise PreprocessingRejection("invalid_audio:non_finite_samples")
    if np.max(np.abs(value)) > 1.00001:
        raise PreprocessingRejection("invalid_audio:samples_out_of_range")
    return value


def _speech_seconds(samples: np.ndarray, sample_rate: int, minimum_rms: float) -> float:
    frame_size = max(1, round(sample_rate * 0.02))
    frame_count = len(samples) // frame_size
    if frame_count == 0:
        return 0.0
    frames = samples[: frame_count * frame_size].reshape(frame_count, frame_size)
    frame_rms = np.sqrt(np.mean(np.square(frames), axis=1))
    return float(np.count_nonzero(frame_rms >= minimum_rms) * frame_size / sample_rate)


def _acoustic_fingerprint(samples: np.ndarray) -> np.ndarray:
    windowed = samples.astype(np.float64) * np.hanning(len(samples))
    spectrum = np.log1p(np.abs(np.fft.rfft(windowed)))
    source_axis = np.linspace(0.0, 1.0, num=len(spectrum))
    fingerprint = np.interp(np.linspace(0.0, 1.0, num=64), source_axis, spectrum)
    fingerprint -= float(np.mean(fingerprint))
    norm = float(np.linalg.norm(fingerprint))
    if norm > 1e-12:
        fingerprint /= norm
    return fingerprint.astype(np.float32)


def preprocess_samples(
    samples: np.ndarray,
    sample_rate: int,
    *,
    policy: AudioPolicy | None = None,
) -> PreparedAudio:
    """Convert to the SSOT audio contract and enforce corpus quality gates."""
    selected = policy or AudioPolicy()
    if sample_rate <= 0:
        raise PreprocessingRejection("invalid_audio:sample_rate")
    mono = _float_mono(samples)
    duration = len(mono) / sample_rate
    if not selected.min_duration_seconds <= duration <= selected.max_duration_seconds:
        raise PreprocessingRejection("unsupported_duration")

    peak = float(np.max(np.abs(mono)))
    clipping_ratio = float(np.mean(np.abs(mono) >= selected.clipping_amplitude))
    if clipping_ratio > selected.max_clipping_ratio:
        raise PreprocessingRejection("excessive_clipping")

    divisor = gcd(sample_rate, selected.target_sample_rate)
    if sample_rate != selected.target_sample_rate:
        mono = resample_poly(
            mono,
            selected.target_sample_rate // divisor,
            sample_rate // divisor,
        )
    converted = np.asarray(np.clip(mono, -1.0, 1.0), dtype=np.float32)
    rms = float(np.sqrt(np.mean(np.square(converted, dtype=np.float64))))
    speech_seconds = _speech_seconds(converted, selected.target_sample_rate, selected.min_rms)
    if rms < selected.min_rms or speech_seconds < selected.min_speech_seconds:
        raise PreprocessingRejection("no_speech")

    pcm_sha256 = hashlib.sha256(converted.tobytes(order="C")).hexdigest()
    return PreparedAudio(
        samples=converted,
        sample_rate=selected.target_sample_rate,
        duration_seconds=len(converted) / selected.target_sample_rate,
        speech_seconds=speech_seconds,
        rms=rms,
        peak=peak,
        clipping_ratio=clipping_ratio,
        pcm_sha256=pcm_sha256,
        fingerprint=_acoustic_fingerprint(converted),
    )


def map_transcript_to_word(
    transcript: str | None,
    registry: VocabularyRegistry,
) -> str | None:
    """Map an entire normalized utterance; sentence substring matches are forbidden."""
    if transcript is None:
        return None
    normalized = unicodedata.normalize("NFC", transcript).strip()
    for entry in registry.entries:
        if normalized == entry.canonical_tamil or normalized in entry.aliases:
            return entry.word_id
    return None


def assign_speaker_split(
    speaker_pseudonym: str,
    *,
    seed: int,
) -> Literal["train", "calibration", "evaluation"]:
    if not speaker_pseudonym:
        raise ValueError("speaker_pseudonym is required")
    digest = hashlib.sha256(f"{seed}:{speaker_pseudonym}".encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "calibration"
    return "evaluation"


class DuplicateTracker:
    """Reject exact PCM duplicates and normalized spectral near-duplicates."""

    def __init__(self, policy: AudioPolicy | None = None) -> None:
        self.policy = policy or AudioPolicy()
        self._exact: dict[str, str] = {}
        self._fingerprints: list[tuple[str, np.ndarray]] = []

    def accept(self, sample_id: str, prepared: PreparedAudio) -> str | None:
        exact_owner = self._exact.get(prepared.pcm_sha256)
        if exact_owner is not None:
            return f"exact_duplicate:{exact_owner}"
        for owner, fingerprint in self._fingerprints:
            similarity = float(np.dot(fingerprint, prepared.fingerprint))
            if similarity >= self.policy.near_duplicate_similarity:
                return f"acoustic_near_duplicate:{owner}"
        self._exact[prepared.pcm_sha256] = sample_id
        self._fingerprints.append((sample_id, prepared.fingerprint))
        return None


def _decode_audio_file(path: Path) -> tuple[int, np.ndarray]:
    if path.suffix.casefold() == ".wav":
        try:
            sample_rate, samples = wavfile.read(path)
            return int(sample_rate), samples
        except Exception as exc:
            raise PreprocessingRejection("undecodable_audio") from exc
    try:
        with TemporaryDirectory(prefix="vaakmitra_preprocess_") as temporary:
            decoded = Path(temporary) / "decoded.wav"
            completed = subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(path),
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    "-y",
                    str(decoded),
                ],
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0 or not decoded.is_file():
                raise PreprocessingRejection("undecodable_audio")
            sample_rate, samples = wavfile.read(decoded)
            return int(sample_rate), samples
    except OSError as exc:
        raise PreprocessingRejection("decoder_unavailable") from exc


def _safe_source_path(root: Path, relative: str) -> Path:
    resolved_root = root.resolve()
    path = (resolved_root / relative).resolve()
    try:
        path.relative_to(resolved_root)
    except ValueError as exc:
        raise PreprocessingRejection("audio_path_outside_root") from exc
    return path


def preprocess_manifest(
    manifest_path: Path | str,
    *,
    audio_root: Path | str,
    output_root: Path | str,
    registry: VocabularyRegistry,
    seed: int,
    policy: AudioPolicy | None = None,
) -> PreprocessingReport:
    """Stream a source manifest into immutable prepared WAVs and derived records."""
    selected = policy or AudioPolicy()
    source_root = Path(audio_root)
    build_root = Path(output_root)
    output_manifest = build_root / "manifest.jsonl"
    if output_manifest.exists():
        raise FileExistsError(output_manifest)
    build_root.mkdir(parents=True, exist_ok=True)
    audio_output = build_root / "audio"
    audio_output.mkdir(parents=True, exist_ok=True)

    tracker = DuplicateTracker(selected)
    accepted = 0
    rejections: Counter[str] = Counter()
    with Path(manifest_path).open("r", encoding="utf-8") as source, output_manifest.open(
        "x", encoding="utf-8"
    ) as sink:
        for line in source:
            if not line.strip():
                continue
            try:
                record = CorpusRecord.model_validate(json.loads(line))
                source_path = _safe_source_path(source_root, record.audio_path)
                if not source_path.is_file():
                    raise PreprocessingRejection("audio_unavailable")
                if hashlib.sha256(source_path.read_bytes()).hexdigest() != record.audio_sha256:
                    raise PreprocessingRejection("source_integrity_mismatch")
                sample_rate, samples = _decode_audio_file(source_path)
                prepared = preprocess_samples(samples, sample_rate, policy=selected)
                duplicate_reason = tracker.accept(record.sample_id, prepared)
                if duplicate_reason is not None:
                    raise PreprocessingRejection(duplicate_reason.split(":", 1)[0])
                mapped_word_id = map_transcript_to_word(record.transcript, registry)
                if record.label_kind == "target" and mapped_word_id != record.canonical_word_id:
                    raise PreprocessingRejection("target_transcript_mismatch")

                filename = f"{hashlib.sha256(record.sample_id.encode('utf-8')).hexdigest()[:24]}.wav"
                relative_output = Path("audio") / filename
                destination = audio_output / filename
                pcm16 = np.rint(np.clip(prepared.samples, -1.0, 1.0) * 32767.0).astype("<i2")
                wavfile.write(destination, selected.target_sample_rate, pcm16)
                output_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
                derived = CorpusRecord(
                    schema_version="vaakmitra-corpus-record-1",
                    sample_id=f"{record.sample_id}-prep16k",
                    source_id=record.source_id,
                    source_revision=record.source_revision,
                    original_id=record.original_id,
                    speaker_pseudonym=record.speaker_pseudonym,
                    canonical_word_id=mapped_word_id,
                    label_kind="target" if mapped_word_id else "other",
                    transcript=record.transcript,
                    audio_path=relative_output.as_posix(),
                    audio_sha256=output_hash,
                    duration_seconds=prepared.duration_seconds,
                    split=assign_speaker_split(record.speaker_pseudonym, seed=seed),
                    licence_id=record.licence_id,
                    provenance_kind="augmented",
                    parent_id=record.sample_id,
                    transformation="decode_resample_16k_mono",
                )
                sink.write(derived.model_dump_json() + "\n")
                sink.flush()
                accepted += 1
            except (json.JSONDecodeError, ValidationError) as exc:
                rejections[f"invalid_record:{type(exc).__name__}"] += 1
            except PreprocessingRejection as exc:
                rejections[str(exc)] += 1

    report = PreprocessingReport(
        accepted=accepted,
        rejected=sum(rejections.values()),
        rejection_counts=dict(sorted(rejections.items())),
        manifest_path=output_manifest,
    )
    (build_root / "report.json").write_text(
        json.dumps(
            {
                "schema_version": "vaakmitra-preprocessing-report-1",
                "accepted": report.accepted,
                "rejected": report.rejected,
                "rejection_counts": report.rejection_counts,
                "seed": seed,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return report
