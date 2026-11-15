"""DEC-028/MST-001..004: mobile-student data is deterministic and leakage-safe."""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
import pytest

from app.vaakmitra_word.mobile_student_data import (
    MOBILE_LABELS,
    MobileStudentDataError,
    TeacherTargetIndex,
    augment_mobile_channel,
    load_mobile_samples,
    preprocess_pcm16,
    time_scale_mobile_waveform,
)


EXPECTED_LABELS = (
    "TA_WORD_0001", "TA_WORD_0002", "TA_WORD_0012", "TA_WORD_0013",
    "TA_WORD_0014", "TA_WORD_0015", "TA_WORD_0016", "TA_WORD_0017",
    "TA_WORD_0049", "TA_WORD_0050", "TA_WORD_0072", "TA_WORD_0082",
    "TA_WORD_0083", "TA_WORD_0086", "TA_WORD_0090", "TA_WORD_0096",
    "TA_WORD_0098", "TA_WORD_0099", "TA_WORD_0100", "OTHER",
)


def _write_wav(path: Path, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as sink:
        sink.setnchannels(1)
        sink.setsampwidth(2)
        sink.setframerate(16000)
        sink.writeframes(np.asarray(samples, dtype="<i2").tobytes())


def _row(sample_id: str, speaker: str, split: str, audio_path: str, word_id: str | None) -> dict[str, object]:
    return {
        "sample_id": sample_id,
        "speaker_pseudonym": speaker,
        "split": split,
        "audio_path": audio_path,
        "canonical_word_id": word_id,
        "label_kind": "target" if word_id else "other",
        "audio_sha256": "0" * 64,
    }


def test_mst002_label_order_is_exactly_android_starter_words_plus_other() -> None:
    assert MOBILE_LABELS == EXPECTED_LABELS


def test_mst001_pcm_preprocessing_uses_literal_symmetric_pad_and_center_crop() -> None:
    padded = preprocess_pcm16(np.asarray([-32768, 0, 16384], dtype=np.int16), length=7)
    assert padded.tolist() == [0.0, 0.0, -1.0, 0.0, 0.5, 0.0, 0.0]

    cropped = preprocess_pcm16(np.arange(9, dtype=np.int16), length=5)
    assert cropped.tolist() == pytest.approx([2 / 32768, 3 / 32768, 4 / 32768, 5 / 32768, 6 / 32768])


def test_mst013_channel_augmentation_is_seeded_bounded_and_trainable() -> None:
    waveform = np.zeros(32_000, dtype=np.float32)
    waveform[15_900:16_100] = 0.25
    first = augment_mobile_channel(waveform, seed=1701)
    repeated = augment_mobile_channel(waveform, seed=1701)
    different = augment_mobile_channel(waveform, seed=1702)
    assert first.dtype == np.float32
    assert first.shape == waveform.shape
    assert np.array_equal(first, repeated)
    assert not np.array_equal(first, different)
    assert np.isfinite(first).all()
    assert float(np.max(np.abs(first))) <= 1.0
    assert np.count_nonzero(first) > np.count_nonzero(waveform)


def test_mst013_time_scaling_changes_active_duration_but_preserves_contract() -> None:
    waveform = np.zeros(1_000, dtype=np.float32)
    waveform[450:550] = 1.0
    stretched = time_scale_mobile_waveform(waveform, factor=2.0)
    compressed = time_scale_mobile_waveform(waveform, factor=0.75)
    assert stretched.shape == waveform.shape == compressed.shape
    assert np.count_nonzero(stretched > 0.5) > np.count_nonzero(waveform > 0.5)
    assert np.count_nonzero(compressed > 0.5) < np.count_nonzero(waveform > 0.5)


def test_mst003_manifest_maps_null_to_other_and_rejects_speaker_leakage(tmp_path: Path) -> None:
    audio_root = tmp_path / "audio"
    _write_wav(audio_root / "a.wav", np.ones(6400, dtype=np.int16))
    _write_wav(audio_root / "b.wav", np.ones(6400, dtype=np.int16))
    manifest = tmp_path / "manifest.jsonl"
    rows = [
        _row("a", "speaker-1", "train", "a.wav", "TA_WORD_0001"),
        _row("b", "speaker-1", "evaluation", "b.wav", None),
    ]
    manifest.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    with pytest.raises(MobileStudentDataError, match="speaker_split_leakage"):
        load_mobile_samples(manifest, audio_root, verify_hashes=False)


def test_mst003_manifest_rejects_missing_audio_and_child_roots(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(_row("a", "speaker-1", "train", "missing.wav", None)) + "\n", encoding="utf-8")
    with pytest.raises(MobileStudentDataError, match="audio_missing"):
        load_mobile_samples(manifest, tmp_path / "audio", verify_hashes=False)

    inventoried = load_mobile_samples(
        manifest,
        tmp_path / "audio",
        verify_hashes=False,
        verify_files=False,
    )
    assert inventoried[0].audio_path == tmp_path / "audio" / "missing.wav"

    child_root = tmp_path / "eval" / "child"
    _write_wav(child_root / "a.wav", np.ones(6400, dtype=np.int16))
    with pytest.raises(MobileStudentDataError, match="child_data_prohibited"):
        load_mobile_samples(manifest, child_root, verify_hashes=False)


def test_mst003_manifest_rejects_lexical_audio_path_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside.wav"
    _write_wav(outside, np.ones(6400, dtype=np.int16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        json.dumps(_row("escape", "speaker-1", "train", "../outside.wav", None)) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(MobileStudentDataError, match="audio_path_escape"):
        load_mobile_samples(manifest, tmp_path / "audio", verify_hashes=False)


def test_mst004_teacher_index_applies_frozen_classifier_to_embedding_shard(tmp_path: Path) -> None:
    labels = np.asarray(["TA_WORD_0001", "OTHER"])
    classifier = tmp_path / "classifier.npz"
    np.savez(
        classifier,
        labels=labels,
        weights=np.asarray([[1.0, 0.0], [-1.0, 0.0]]),
        bias=np.asarray([0.0, 0.0]),
        pooling_schema=np.asarray("mean-std-v1"),
        feature_means=np.asarray([0.0, 0.0]),
        feature_scales=np.asarray([1.0, 1.0]),
        temperature=np.asarray(1.0),
    )
    manifest = {
        "records": [{
            "sample_id": "sample-1",
            "embedding_key": "embedding__000000",
            "canonical_word_id": "TA_WORD_0001",
            "speaker_pseudonym": "speaker-1",
            "split": "train",
        }]
    }
    shard = tmp_path / "shard-00001.npz"
    np.savez(shard, manifest=np.asarray(json.dumps(manifest)), embedding__000000=np.asarray([[2.0]], dtype=np.float32))

    index = TeacherTargetIndex.from_artifacts(classifier, [shard])
    probabilities = index.probabilities_for("sample-1")
    assert probabilities is not None
    assert probabilities.tolist() == pytest.approx([0.98201379, 0.01798621], rel=1e-6)

    cache = tmp_path / "teacher-targets.npz"
    index.save(cache)
    restored = TeacherTargetIndex.load(cache)
    assert restored.labels == ("TA_WORD_0001", "OTHER")
    assert restored.probabilities_for("sample-1").tolist() == pytest.approx(probabilities.tolist())
