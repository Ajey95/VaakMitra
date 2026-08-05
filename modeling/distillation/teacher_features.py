"""Safe local packaging for adult Tamil teacher-model feature tensors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field

Sha256 = str


class TeacherModelConfig(BaseModel):
    """Pinned research configuration for the upstream teacher model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: Literal["ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large"]
    revision: str = Field(pattern=r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
    license_spdx: Literal["MIT"]
    sample_rate_hz: Literal[16000]
    frame_shift_ms: float = Field(gt=0)
    source_scope: Literal["adult_tamil_teacher"]
    storage_policy: Literal["local_only_voice_derived"]
    direct_phoneme_posteriors_supported: Literal[False]
    production_ready: Literal[False]


class TeacherFeatureManifest(BaseModel):
    """Provenance attached to one local feature tensor cache."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    model_id: Literal["ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large"]
    model_revision: str = Field(pattern=r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
    model_license_spdx: Literal["MIT"]
    sample_rate_hz: Literal[16000]
    frame_shift_ms: float = Field(gt=0)
    frame_count: int = Field(gt=0)
    feature_dimension: int = Field(gt=0)
    audio_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    feature_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    source_scope: Literal["adult_tamil_teacher"]
    storage_policy: Literal["local_only_voice_derived"]
    direct_phoneme_posteriors_supported: Literal[False]


FloatFeatures = npt.NDArray[np.float32]


def load_teacher_config(path: Path) -> TeacherModelConfig:
    """Load a pinned teacher configuration from UTF-8 JSON."""

    return TeacherModelConfig.model_validate_json(path.read_text(encoding="utf-8"))


def _validate_features(features: npt.NDArray[np.generic]) -> FloatFeatures:
    if not isinstance(features, np.ndarray):
        raise TypeError("features must be a NumPy array")
    if features.dtype != np.float32:
        raise ValueError("features must use float32")
    if features.ndim != 2 or features.shape[0] == 0 or features.shape[1] == 0:
        raise ValueError("features must be a non-empty [frames, dimension] tensor")
    if not np.isfinite(features).all():
        raise ValueError("features must contain only finite values")
    return np.ascontiguousarray(features)


def _feature_digest(features: FloatFeatures) -> str:
    digest = hashlib.sha256()
    digest.update(str(features.dtype).encode("ascii"))
    digest.update(json.dumps(features.shape).encode("ascii"))
    digest.update(features.tobytes(order="C"))
    return digest.hexdigest()


def write_teacher_feature_cache(
    path: Path,
    features: npt.NDArray[np.generic],
    *,
    model_config: TeacherModelConfig,
    audio_sha256: str,
) -> TeacherFeatureManifest:
    """Write features plus provenance, refusing any overwrite."""

    validated = _validate_features(features)
    manifest = TeacherFeatureManifest(
        schema_version="1.0",
        model_id=model_config.model_id,
        model_revision=model_config.revision,
        model_license_spdx=model_config.license_spdx,
        sample_rate_hz=model_config.sample_rate_hz,
        frame_shift_ms=model_config.frame_shift_ms,
        frame_count=validated.shape[0],
        feature_dimension=validated.shape[1],
        audio_sha256=audio_sha256,
        feature_sha256=_feature_digest(validated),
        source_scope=model_config.source_scope,
        storage_policy=model_config.storage_policy,
        direct_phoneme_posteriors_supported=False,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with path.open("xb") as cache_file:
            created = True
            np.savez_compressed(
                cache_file,
                features=validated,
                manifest_json=np.array(manifest.model_dump_json()),
            )
    except Exception:
        if created and path.exists():
            path.unlink()
        raise
    return manifest


def read_teacher_feature_cache(path: Path) -> tuple[FloatFeatures, TeacherFeatureManifest]:
    """Load a cache and verify its feature tensor against the manifest digest."""

    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != {"features", "manifest_json"}:
            raise ValueError("teacher cache contains unexpected fields")
        features = _validate_features(archive["features"])
        manifest = TeacherFeatureManifest.model_validate_json(
            str(archive["manifest_json"].item())
        )

    if features.shape != (manifest.frame_count, manifest.feature_dimension):
        raise ValueError("feature shape does not match the manifest")
    if _feature_digest(features) != manifest.feature_sha256:
        raise ValueError("feature digest does not match the manifest")
    return features, manifest
