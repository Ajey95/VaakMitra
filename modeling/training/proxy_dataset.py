"""Local PCM loading and proxy phone-unit tokenization for adult Tamil data."""

from __future__ import annotations

import json
import math
import unicodedata
import wave
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import numpy as np
import torch
from torch.nn import functional as torch_functional


@dataclass(frozen=True, slots=True)
class ProxyIndexRecord:
    audio_rel_path: str
    phonemes: str
    record_id: str
    speaker: str


def proxy_phone_units(phoneme_text: str) -> tuple[str, ...]:
    """Return deterministic Unicode IPA units, excluding whitespace and punctuation."""

    normalized = unicodedata.normalize("NFD", phoneme_text)
    return tuple(
        character
        for character in normalized
        if unicodedata.category(character)[0] in {"L", "M"}
    )


def load_mono_pcm16(
    path: str | Path,
    *,
    target_sample_rate: int = 16000,
    max_duration_seconds: float = 8.0,
) -> torch.Tensor:
    """Load uncompressed mono PCM16 and resample without persistent intermediates."""

    if target_sample_rate <= 0:
        raise ValueError("target_sample_rate must be positive")
    if not math.isfinite(max_duration_seconds) or max_duration_seconds <= 0:
        raise ValueError("max_duration_seconds must be finite and positive")
    with wave.open(str(path), "rb") as source:
        if source.getnchannels() != 1:
            raise ValueError("audio must be mono")
        if source.getsampwidth() != 2 or source.getcomptype() != "NONE":
            raise ValueError("audio must be uncompressed PCM16")
        source_rate = source.getframerate()
        frame_count = source.getnframes()
        if frame_count / source_rate > max_duration_seconds:
            raise ValueError("audio exceeds configured maximum duration")
        raw = source.readframes(frame_count)

    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32)
    waveform = torch.from_numpy(samples) / 32768.0
    if source_rate != target_sample_rate:
        target_frames = round(waveform.numel() * target_sample_rate / source_rate)
        waveform = torch_functional.interpolate(
            waveform.reshape(1, 1, -1),
            size=target_frames,
            mode="linear",
            align_corners=False,
        ).reshape(-1)
    return waveform.to(dtype=torch.float32).clamp_(-1.0, 1.0)


def _record_from_json(line: str, line_number: int) -> ProxyIndexRecord:
    try:
        row = json.loads(line)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid proxy index row {line_number}") from error
    if not isinstance(row, dict):
        raise TypeError(f"proxy index row {line_number} must be an object")
    values: dict[str, str] = {}
    for field in ("audio_rel_path", "phonemes", "record_id", "speaker"):
        value = row.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"proxy index row {line_number} requires non-empty {field}")
        values[field] = value.strip()
    audio_path = PurePosixPath(values["audio_rel_path"])
    if audio_path.is_absolute() or ".." in audio_path.parts:
        raise ValueError(f"proxy index row {line_number} contains unsafe audio_rel_path")
    if not proxy_phone_units(values["phonemes"]):
        raise ValueError(f"proxy index row {line_number} has no usable proxy phone units")
    return ProxyIndexRecord(**values)


def select_available_records(
    index_path: str | Path,
    *,
    audio_root: str | Path,
    max_records_per_speaker: int,
    max_duration_seconds: float,
) -> tuple[ProxyIndexRecord, ...]:
    """Select a bounded, speaker-balanced set whose local PCM files are usable."""

    if max_records_per_speaker <= 0:
        raise ValueError("max_records_per_speaker must be positive")
    index = Path(index_path)
    root = Path(audio_root)
    parsed = tuple(
        _record_from_json(line, line_number)
        for line_number, line in enumerate(index.read_text(encoding="utf-8").splitlines(), start=1)
        if line.strip()
    )
    if not parsed:
        raise ValueError("proxy index must contain at least one record")
    record_ids = [record.record_id for record in parsed]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("proxy index record_id values must be unique")

    selected: list[ProxyIndexRecord] = []
    counts: dict[str, int] = {}
    for record in sorted(parsed, key=lambda item: (item.speaker, item.audio_rel_path)):
        if counts.get(record.speaker, 0) >= max_records_per_speaker:
            continue
        audio_path = root / Path(record.audio_rel_path)
        if not audio_path.is_file():
            continue
        try:
            with wave.open(str(audio_path), "rb") as source:
                duration = source.getnframes() / source.getframerate()
                usable = (
                    source.getnchannels() == 1
                    and source.getsampwidth() == 2
                    and source.getcomptype() == "NONE"
                    and duration <= max_duration_seconds
                )
        except (EOFError, wave.Error):
            usable = False
        if not usable:
            continue
        selected.append(record)
        counts[record.speaker] = counts.get(record.speaker, 0) + 1
    if not selected:
        raise ValueError("no locally available proxy records passed audio validation")
    return tuple(selected)
