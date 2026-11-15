"""In-memory WAV preprocessing and neutral quality validation (AU-001..010)."""

from __future__ import annotations

from dataclasses import dataclass
import io
import wave

import numpy as np
from scipy.signal import resample_poly

from .contracts import AudioQuality


TARGET_SAMPLE_RATE = 16000


class UnsupportedAudio(ValueError):
    pass


@dataclass(frozen=True)
class DecodedAudio:
    samples: np.ndarray
    sample_rate: int
    duration_s: float


def decode_wav_bytes(data: bytes) -> DecodedAudio:
    if not data:
        raise UnsupportedAudio("empty audio")
    try:
        with wave.open(io.BytesIO(data), "rb") as source:
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frames = source.readframes(source.getnframes())
    except (wave.Error, EOFError) as exc:
        raise UnsupportedAudio("audio is not a supported PCM WAV") from exc
    if channels < 1 or sample_rate <= 0 or sample_width not in (1, 2, 4):
        raise UnsupportedAudio("unsupported WAV layout")

    if sample_width == 1:
        samples = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_width == 2:
        samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    else:
        samples = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    if samples.size == 0 or samples.size % channels:
        raise UnsupportedAudio("WAV contains no complete audio frames")
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    if not np.isfinite(samples).all():
        raise UnsupportedAudio("decoded audio contains non-finite samples")
    if sample_rate != TARGET_SAMPLE_RATE:
        common = int(np.gcd(sample_rate, TARGET_SAMPLE_RATE))
        samples = resample_poly(samples, TARGET_SAMPLE_RATE // common, sample_rate // common)
    samples = np.asarray(np.clip(samples, -1.0, 1.0), dtype=np.float32)
    return DecodedAudio(samples, TARGET_SAMPLE_RATE, samples.size / TARGET_SAMPLE_RATE)


def validate_audio(samples: np.ndarray, sample_rate: int = TARGET_SAMPLE_RATE) -> AudioQuality:
    audio = np.asarray(samples, dtype=np.float32)
    if audio.ndim != 1 or audio.size == 0 or sample_rate <= 0 or not np.isfinite(audio).all():
        return AudioQuality(reason="invalid_samples")

    duration = audio.size / sample_rate
    absolute = np.abs(audio)
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    peak = float(np.max(absolute))
    clipping_ratio = float(np.mean(absolute >= 0.999))
    clipped = clipping_ratio > 0.01

    frame = max(1, int(sample_rate * 0.03))
    hop = max(1, int(sample_rate * 0.01))
    active_frames = 0
    for start in range(0, max(1, audio.size - frame + 1), hop):
        segment = audio[start : start + frame]
        if segment.size and float(np.mean(np.square(segment, dtype=np.float64))) >= 1e-5:
            active_frames += 1
    speech_duration = min(duration, active_frames * hop / sample_rate)
    speech_detected = speech_duration >= 0.20 and rms >= 0.003
    snr_acceptable = rms >= 0.005

    reason: str | None = None
    if duration < 0.30:
        reason = "too_short"
    elif duration > 12.0:
        reason = "too_long"
    elif clipped:
        reason = "clipped"
    elif not speech_detected:
        reason = "no_speech"
    elif not snr_acceptable:
        reason = "excessive_noise_or_low_level"

    return AudioQuality(
        valid=reason is None,
        speech_detected=speech_detected,
        snr_acceptable=snr_acceptable,
        clipped=clipped,
        duration_s=duration,
        speech_duration_s=speech_duration,
        rms=rms,
        peak=peak,
        clipping_ratio=clipping_ratio,
        reason=reason,
    )

