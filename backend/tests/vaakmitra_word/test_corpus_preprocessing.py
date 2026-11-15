"""Deterministic adult-corpus preprocessing (AU-001..010, DATA-003/007/011)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.io import wavfile

from app.vaakmitra_word.corpus_preprocessing import (
    AudioPolicy,
    DuplicateTracker,
    PreprocessingRejection,
    assign_speaker_split,
    map_transcript_to_word,
    preprocess_manifest,
    preprocess_samples,
)
from app.vaakmitra_word.router import VOCABULARY_REGISTRY


def test_stereo_48khz_audio_becomes_finite_mono_16khz() -> None:
    timeline = np.arange(0, 0.5, 1 / 48_000)
    stereo = np.column_stack(
        (0.2 * np.sin(2 * np.pi * 220 * timeline), 0.1 * np.sin(2 * np.pi * 220 * timeline))
    )

    prepared = preprocess_samples(stereo, 48_000)

    assert prepared.sample_rate == 16_000
    assert prepared.samples.dtype == np.float32
    assert prepared.samples.ndim == 1
    assert prepared.samples.shape == (8_000,)
    assert np.isfinite(prepared.samples).all()


@pytest.mark.parametrize(
    ("samples", "reason"),
    [
        (np.zeros(8_000, dtype=np.float32), "no_speech"),
        (np.full(8_000, np.nan, dtype=np.float32), "invalid_audio"),
        (np.ones(8_000, dtype=np.float32), "excessive_clipping"),
        (np.full(1_000, 0.1, dtype=np.float32), "unsupported_duration"),
    ],
)
def test_quality_gate_rejects_invalid_silence_clipping_and_short_audio(
    samples: np.ndarray,
    reason: str,
) -> None:
    with pytest.raises(PreprocessingRejection, match=reason):
        preprocess_samples(samples, 16_000)


def test_transcript_mapping_is_nfc_exact_and_never_uses_sentence_substrings() -> None:
    assert map_transcript_to_word(" அம்மா ", VOCABULARY_REGISTRY) == "TA_WORD_0001"
    assert map_transcript_to_word("அம்மா வந்தார்", VOCABULARY_REGISTRY) is None
    assert map_transcript_to_word("தெரியாத சொல்", VOCABULARY_REGISTRY) is None


def test_duplicate_tracker_rejects_exact_and_gain_changed_near_duplicates() -> None:
    policy = AudioPolicy(near_duplicate_similarity=0.995)
    tracker = DuplicateTracker(policy)
    timeline = np.arange(0, 0.5, 1 / 16_000)
    original = preprocess_samples(0.2 * np.sin(2 * np.pi * 220 * timeline), 16_000, policy=policy)
    gained = preprocess_samples(0.1 * np.sin(2 * np.pi * 220 * timeline), 16_000, policy=policy)

    assert tracker.accept("first", original) is None
    assert tracker.accept("same-id", original) == "exact_duplicate:first"
    assert tracker.accept("gain-change", gained) == "acoustic_near_duplicate:first"


def test_speaker_split_is_deterministic_and_never_splits_one_speaker() -> None:
    first = assign_speaker_split("speaker-a", seed=20260906)
    assert first in {"train", "calibration", "evaluation"}
    assert assign_speaker_split("speaker-a", seed=20260906) == first
    assert assign_speaker_split("speaker-a", seed=20260907) in {
        "train",
        "calibration",
        "evaluation",
    }


def test_policy_rejects_invalid_threshold_order() -> None:
    with pytest.raises(ValueError, match="duration"):
        AudioPolicy(min_duration_seconds=2.0, max_duration_seconds=1.0)


def test_audio_fingerprint_is_stable_for_identical_samples() -> None:
    timeline = np.arange(0, 0.5, 1 / 16_000)
    samples = 0.2 * np.sin(2 * np.pi * 440 * timeline)
    first = preprocess_samples(samples, 16_000)
    second = preprocess_samples(samples.copy(), 16_000)

    assert first.pcm_sha256 == second.pcm_sha256
    assert hashlib.sha256(first.fingerprint.tobytes()).hexdigest() == hashlib.sha256(
        second.fingerprint.tobytes()
    ).hexdigest()


def test_manifest_preprocessing_writes_traceable_16khz_audio_and_report(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "build"
    source_root.mkdir()
    timeline = np.arange(0, 0.5, 1 / 48_000)
    pcm = np.rint(0.2 * np.sin(2 * np.pi * 220 * timeline) * 32767).astype("<i2")
    source_audio = source_root / "clip.wav"
    wavfile.write(source_audio, 48_000, pcm)
    source_manifest = tmp_path / "source.jsonl"
    source_manifest.write_text(
        json.dumps(
            {
                "schema_version": "vaakmitra-corpus-record-1",
                "sample_id": "adult-one",
                "source_id": "approved-source",
                "source_revision": "revision-one",
                "original_id": "original-one",
                "speaker_pseudonym": "speaker-one",
                "canonical_word_id": "TA_WORD_0001",
                "label_kind": "target",
                "transcript": "அம்மா",
                "audio_path": "clip.wav",
                "audio_sha256": hashlib.sha256(source_audio.read_bytes()).hexdigest(),
                "duration_seconds": 0.5,
                "split": "train",
                "licence_id": "CC-BY-4.0",
                "provenance_kind": "original",
                "parent_id": None,
                "transformation": None,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    report = preprocess_manifest(
        source_manifest,
        audio_root=source_root,
        output_root=output_root,
        registry=VOCABULARY_REGISTRY,
        seed=20260906,
    )

    assert report.accepted == 1
    assert report.rejected == 0
    output_record = json.loads((output_root / "manifest.jsonl").read_text(encoding="utf-8"))
    assert output_record["parent_id"] == "adult-one"
    assert output_record["transformation"] == "decode_resample_16k_mono"
    output_rate, output_samples = wavfile.read(output_root / output_record["audio_path"])
    assert output_rate == 16_000
    assert output_samples.ndim == 1


def test_manifest_preprocessing_refuses_to_overwrite_prior_build(tmp_path: Path) -> None:
    output_root = tmp_path / "build"
    output_root.mkdir()
    (output_root / "manifest.jsonl").write_text("already built\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        preprocess_manifest(
            tmp_path / "missing.jsonl",
            audio_root=tmp_path,
            output_root=output_root,
            registry=VOCABULARY_REGISTRY,
            seed=20260906,
        )
