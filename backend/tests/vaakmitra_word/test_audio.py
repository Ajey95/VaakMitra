from __future__ import annotations

import io
import wave

import numpy as np

from app.vaakmitra_word.audio import decode_wav_bytes, validate_audio


def stereo_wav(sample_rate: int = 8000, duration_s: float = 1.0) -> bytes:
    t = np.arange(int(sample_rate * duration_s)) / sample_rate
    mono = 0.2 * np.sin(2 * np.pi * 220 * t)
    stereo = np.column_stack((mono, mono * 0.5))
    pcm = (stereo * 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())
    return buffer.getvalue()


def test_pcm_wav_becomes_mono_float32_16khz() -> None:
    decoded = decode_wav_bytes(stereo_wav())

    assert decoded.sample_rate == 16000
    assert decoded.samples.dtype == np.float32
    assert decoded.samples.ndim == 1
    assert decoded.duration_s == 1.0


def test_clipping_is_invalid() -> None:
    quality = validate_audio(np.ones(16000, dtype=np.float32), 16000)

    assert quality.clipped is True
    assert quality.valid is False
    assert quality.reason == "clipped"


def test_silence_is_invalid_without_pronunciation_judgement() -> None:
    quality = validate_audio(np.zeros(16000, dtype=np.float32), 16000)

    assert quality.valid is False
    assert quality.speech_detected is False
    assert quality.reason == "no_speech"


def test_clear_tone_is_valid_engineering_audio() -> None:
    decoded = decode_wav_bytes(stereo_wav(sample_rate=16000))

    quality = validate_audio(decoded.samples, decoded.sample_rate)

    assert quality.valid is True
    assert quality.speech_detected is True

