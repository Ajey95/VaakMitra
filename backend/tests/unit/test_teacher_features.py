from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from modeling.distillation.teacher_features import (
    TeacherFeatureManifest,
    load_teacher_config,
    read_teacher_feature_cache,
    write_teacher_feature_cache,
)
from pydantic import ValidationError

CONFIG_PATH = Path("modeling/configs/indicconformer_teacher.json")


def _features() -> np.ndarray:
    return np.arange(24, dtype=np.float32).reshape(6, 4)


def _write(path: Path) -> TeacherFeatureManifest:
    return write_teacher_feature_cache(
        path,
        _features(),
        model_config=load_teacher_config(CONFIG_PATH),
        audio_sha256="a" * 64,
    )


def test_pinned_teacher_config_is_research_only() -> None:
    config = load_teacher_config(CONFIG_PATH)

    assert config.model_id == "ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large"
    assert len(config.revision) == 40
    assert config.license_spdx == "MIT"
    assert config.sample_rate_hz == 16_000
    assert config.source_scope == "adult_tamil_teacher"
    assert config.direct_phoneme_posteriors_supported is False
    assert config.production_ready is False


def test_cache_round_trip_preserves_features_and_safe_manifest(tmp_path: Path) -> None:
    path = tmp_path / "teacher-features.npz"
    written = _write(path)

    features, loaded = read_teacher_feature_cache(path)

    np.testing.assert_array_equal(features, _features())
    assert loaded == written
    assert loaded.frame_count == 6
    assert loaded.feature_dimension == 4
    assert loaded.storage_policy == "local_only_voice_derived"
    assert loaded.direct_phoneme_posteriors_supported is False
    assert loaded.audio_sha256 == "a" * 64
    assert len(loaded.feature_sha256) == 64
    manifest_payload = loaded.model_dump_json()
    assert str(tmp_path) not in manifest_payload
    assert "audio_path" not in manifest_payload


def test_cache_archive_contains_only_features_and_manifest(tmp_path: Path) -> None:
    path = tmp_path / "teacher-features.npz"
    _write(path)

    with np.load(path, allow_pickle=False) as archive:
        assert set(archive.files) == {"features", "manifest_json"}
        json.loads(str(archive["manifest_json"].item()))


@pytest.mark.parametrize(
    "features",
    [
        np.zeros((2, 3), dtype=np.float64),
        np.zeros((2, 3, 1), dtype=np.float32),
        np.zeros((0, 3), dtype=np.float32),
        np.array([[0.0, np.nan]], dtype=np.float32),
    ],
)
def test_writer_rejects_invalid_feature_tensors(tmp_path: Path, features: np.ndarray) -> None:
    with pytest.raises(ValueError):
        write_teacher_feature_cache(
            tmp_path / "bad.npz",
            features,
            model_config=load_teacher_config(CONFIG_PATH),
            audio_sha256="a" * 64,
        )


def test_writer_refuses_to_overwrite_voice_derived_cache(tmp_path: Path) -> None:
    path = tmp_path / "teacher-features.npz"
    _write(path)

    with pytest.raises(FileExistsError):
        _write(path)


def test_manifest_rejects_non_sha_audio_digest() -> None:
    payload = {
        "schema_version": "1.0",
        "model_id": "ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large",
        "model_revision": "b" * 40,
        "model_license_spdx": "MIT",
        "sample_rate_hz": 16_000,
        "frame_shift_ms": 10.0,
        "frame_count": 2,
        "feature_dimension": 3,
        "audio_sha256": "not-a-digest",
        "feature_sha256": "c" * 64,
        "source_scope": "adult_tamil_teacher",
        "storage_policy": "local_only_voice_derived",
        "direct_phoneme_posteriors_supported": False,
    }

    with pytest.raises(ValidationError):
        TeacherFeatureManifest.model_validate(payload)


def test_reader_detects_feature_tampering(tmp_path: Path) -> None:
    path = tmp_path / "teacher-features.npz"
    manifest = _write(path)
    changed = _features().copy()
    changed[0, 0] = 999.0
    with path.open("wb") as cache_file:
        np.savez_compressed(
            cache_file,
            features=changed,
            manifest_json=np.array(manifest.model_dump_json()),
        )

    with pytest.raises(ValueError, match="digest"):
        read_teacher_feature_cache(path)
