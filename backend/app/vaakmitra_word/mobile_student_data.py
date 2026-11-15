"""Adult/public data contracts for the DEC-028 mobile engineering student."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable
import wave

import numpy as np

from .classifier_training import pool_embedding


MOBILE_LABELS = (
    "TA_WORD_0001", "TA_WORD_0002", "TA_WORD_0012", "TA_WORD_0013",
    "TA_WORD_0014", "TA_WORD_0015", "TA_WORD_0016", "TA_WORD_0017",
    "TA_WORD_0049", "TA_WORD_0050", "TA_WORD_0072", "TA_WORD_0082",
    "TA_WORD_0083", "TA_WORD_0086", "TA_WORD_0090", "TA_WORD_0096",
    "TA_WORD_0098", "TA_WORD_0099", "TA_WORD_0100", "OTHER",
)
VALID_SPLITS = frozenset({"train", "calibration", "evaluation"})


def time_scale_mobile_waveform(waveform: np.ndarray, *, factor: float) -> np.ndarray:
    """MST-013: linearly scale duration, then restore the fixed input length."""
    source = np.asarray(waveform, dtype=np.float32)
    if source.ndim != 1 or source.size == 0 or not np.isfinite(source).all() or not 0.5 <= factor <= 3.0:
        raise MobileStudentDataError("time_scale_invalid")
    scaled_length = max(1, int(round(source.size * factor)))
    positions = np.linspace(0.0, source.size - 1.0, scaled_length, dtype=np.float64)
    scaled = np.interp(positions, np.arange(source.size, dtype=np.float64), source).astype(np.float32)
    if scaled_length >= source.size:
        start = (scaled_length - source.size) // 2
        return scaled[start : start + source.size].copy()
    output = np.zeros_like(source)
    start = (source.size - scaled_length) // 2
    output[start : start + scaled_length] = scaled
    return output


def augment_mobile_channel(waveform: np.ndarray, *, seed: int) -> np.ndarray:
    """MST-013: deterministic bounded speaker/room/microphone simulation."""
    source = np.asarray(waveform, dtype=np.float32)
    if source.ndim != 1 or source.size == 0 or not np.isfinite(source).all():
        raise MobileStudentDataError("augmentation_input_invalid")
    rng = np.random.default_rng(seed)

    # Preserve a substantial mild-channel share while exposing the student to
    # large speaking-rate and room-envelope shifts on the remaining examples.
    strong_channel = float(rng.random()) >= 0.65
    time_factor = float(rng.uniform(0.75, 2.25)) if strong_channel else 1.0
    result = time_scale_mobile_waveform(source, factor=time_factor)

    shift = int(rng.integers(-1200, 1201))
    result = np.roll(result, shift).astype(np.float32, copy=False)
    if shift > 0:
        result[:shift] = 0.0
    elif shift < 0:
        result[shift:] = 0.0

    # Moving-average coloration approximates the bandwidth loss of small
    # speakers and microphones without adding a deployment-time dependency.
    smoothing_width = int(rng.choice(np.asarray([1, 3, 5, 7], dtype=np.int64)))
    if smoothing_width > 1:
        kernel = np.full(smoothing_width, 1.0 / smoothing_width, dtype=np.float32)
        result = np.convolve(result, kernel, mode="same").astype(np.float32)

    dry = result.copy()
    delay = int(rng.integers(160, 6_401 if strong_channel else 961))
    echo_gain = float(rng.uniform(0.05, 0.35))
    result[delay:] += dry[:-delay] * echo_gain
    second_delay = min(delay * 2, result.size - 1)
    if second_delay > 0:
        result[second_delay:] += dry[:-second_delay] * (echo_gain * 0.35)

    gain = float(rng.uniform(0.65, 1.15))
    noise_scale = float(rng.uniform(0.0002, 0.006))
    noise = rng.normal(0.0, noise_scale, size=result.shape).astype(np.float32)
    return np.clip(result * gain + noise, -1.0, 1.0).astype(np.float32)


class MobileStudentDataError(RuntimeError):
    """MST-001..004 input evidence cannot be used safely."""


@dataclass(frozen=True)
class MobileSample:
    sample_id: str
    speaker_pseudonym: str
    split: str
    label: str
    audio_path: Path
    audio_sha256: str


def preprocess_pcm16(samples: np.ndarray, *, length: int = 32_000) -> np.ndarray:
    """MST-001: convert PCM16 and symmetrically pad or centre crop."""
    values = np.asarray(samples)
    if values.ndim != 1 or values.dtype != np.int16 or length < 1:
        raise MobileStudentDataError("pcm16_invalid")
    if values.size > length:
        start = (values.size - length) // 2
        values = values[start : start + length]
    result = np.zeros(length, dtype=np.float32)
    start = (length - values.size) // 2
    result[start : start + values.size] = values.astype(np.float32) / 32768.0
    return result


def read_pcm16_wav(path: Path | str) -> np.ndarray:
    """Read the governed mono 16 kHz PCM16 corpus format."""
    source = Path(path)
    try:
        with wave.open(str(source), "rb") as reader:
            if reader.getnchannels() != 1 or reader.getsampwidth() != 2 or reader.getframerate() != 16_000:
                raise MobileStudentDataError("wav_contract_mismatch")
            return np.frombuffer(reader.readframes(reader.getnframes()), dtype="<i2").copy()
    except MobileStudentDataError:
        raise
    except (OSError, wave.Error, EOFError) as exc:
        raise MobileStudentDataError("wav_decode_failed") from exc


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_mobile_samples(
    manifest_path: Path | str,
    audio_root: Path | str,
    *,
    verify_hashes: bool = True,
    verify_files: bool = True,
) -> tuple[MobileSample, ...]:
    """MST-002/003: load only registered adult/public speaker-disjoint rows."""
    manifest = Path(manifest_path)
    # MST-003: avoid a filesystem-resolving syscall for every corpus row while
    # retaining a strict lexical containment check for the immutable manifest.
    root = Path(audio_root).absolute()
    lowered_parts = {part.lower() for part in root.parts}
    if "child" in lowered_parts or "eval" in lowered_parts:
        raise MobileStudentDataError("child_data_prohibited")

    samples: list[MobileSample] = []
    seen_ids: set[str] = set()
    speaker_splits: dict[str, str] = {}
    with manifest.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MobileStudentDataError(f"manifest_json_invalid:{line_number}") from exc
            word_id = row.get("canonical_word_id")
            label = str(word_id) if word_id else "OTHER"
            if label not in MOBILE_LABELS or row.get("split") not in VALID_SPLITS:
                continue
            sample_id = str(row.get("sample_id", ""))
            speaker = str(row.get("speaker_pseudonym", ""))
            split = str(row["split"])
            if not sample_id or not speaker or sample_id in seen_ids:
                raise MobileStudentDataError("sample_identity_invalid")
            prior = speaker_splits.setdefault(speaker, split)
            if prior != split:
                raise MobileStudentDataError("speaker_split_leakage")
            relative = Path(str(row.get("audio_path", "")))
            if relative.is_absolute() or ".." in relative.parts:
                raise MobileStudentDataError("audio_path_escape")
            audio_path = root / relative
            if verify_files and not audio_path.is_file():
                raise MobileStudentDataError(f"audio_missing:{sample_id}")
            expected_hash = str(row.get("audio_sha256", "")).lower()
            if verify_hashes and (not verify_files or _sha256_file(audio_path) != expected_hash):
                raise MobileStudentDataError(f"audio_hash_mismatch:{sample_id}")
            seen_ids.add(sample_id)
            samples.append(MobileSample(sample_id, speaker, split, label, audio_path, expected_hash))
    if not samples:
        raise MobileStudentDataError("no_mobile_samples")
    return tuple(samples)


@dataclass(frozen=True)
class TeacherTargetIndex:
    """MST-004 soft-label index produced by the frozen teacher classifier."""

    labels: tuple[str, ...]
    probabilities: dict[str, np.ndarray]

    @classmethod
    def from_artifacts(cls, classifier_path: Path | str, shard_paths: Iterable[Path | str]) -> "TeacherTargetIndex":
        with np.load(classifier_path, allow_pickle=False) as artifact:
            labels = tuple(str(value) for value in artifact["labels"].tolist())
            weights = np.asarray(artifact["weights"], dtype=np.float64)
            bias = np.asarray(artifact["bias"], dtype=np.float64)
            means = np.asarray(artifact["feature_means"], dtype=np.float64)
            scales = np.asarray(artifact["feature_scales"], dtype=np.float64)
            temperature = float(artifact["temperature"])
            schema = str(artifact["pooling_schema"])
        if weights.shape[0] != len(labels) or temperature <= 0 or np.any(scales <= 0):
            raise MobileStudentDataError("teacher_classifier_invalid")

        output: dict[str, np.ndarray] = {}
        for shard_path in shard_paths:
            with np.load(shard_path, allow_pickle=False) as shard:
                manifest = json.loads(str(shard["manifest"]))
                for record in manifest.get("records", []):
                    sample_id = str(record["sample_id"])
                    if sample_id in output:
                        raise MobileStudentDataError("teacher_sample_duplicate")
                    pooled = pool_embedding(np.asarray(shard[str(record["embedding_key"])]), schema=schema)
                    standardized = (pooled - means) / scales
                    logits = (standardized @ weights.T + bias) / temperature
                    logits -= logits.max()
                    probabilities = np.exp(logits)
                    output[sample_id] = (probabilities / probabilities.sum()).astype(np.float32)
        return cls(labels=labels, probabilities=output)

    def probabilities_for(self, sample_id: str) -> np.ndarray | None:
        value = self.probabilities.get(sample_id)
        return None if value is None else value.copy()

    def save(self, path: Path | str) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        sample_ids = sorted(self.probabilities)
        values = np.vstack([self.probabilities[sample_id] for sample_id in sample_ids]).astype(np.float32)
        np.savez_compressed(
            destination,
            labels=np.asarray(self.labels),
            sample_ids=np.asarray(sample_ids),
            probabilities=values,
        )

    @classmethod
    def load(cls, path: Path | str) -> "TeacherTargetIndex":
        with np.load(path, allow_pickle=False) as cache:
            labels = tuple(str(value) for value in cache["labels"].tolist())
            sample_ids = [str(value) for value in cache["sample_ids"].tolist()]
            values = np.asarray(cache["probabilities"], dtype=np.float32)
        if values.shape != (len(sample_ids), len(labels)) or not np.isfinite(values).all():
            raise MobileStudentDataError("teacher_cache_invalid")
        return cls(labels, {sample_id: values[index] for index, sample_id in enumerate(sample_ids)})
