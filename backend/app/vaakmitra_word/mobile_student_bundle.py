"""Hash-bound bundle and adult engineering policy for DEC-028/029."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

import numpy as np


REQUIRED_RUNTIME_FILES = (
    "mobile_word_student.int8.onnx",
    "labels.json",
    "reference_bank.json",
    "adult_engineering_calibration.json",
    "silero_vad.onnx",
)


class BundleIntegrityError(RuntimeError):
    """MST-006 runtime evidence is missing, changed, or unsafe."""


@dataclass(frozen=True)
class ReferenceExample:
    sample_id: str
    speaker_pseudonym: str
    label: str
    embedding: np.ndarray


@dataclass(frozen=True)
class ReferenceCentroid:
    centroid: np.ndarray
    sample_ids: tuple[str, ...]
    speaker_count: int


@dataclass(frozen=True)
class MobileCalibration:
    labels: tuple[str, ...]
    low_thresholds: dict[str, float]
    high_thresholds: dict[str, float]
    minimum_margin: float = 0.10
    minimum_similarity: float = 0.60


@dataclass(frozen=True)
class DevelopmentEvidence:
    result: str
    reason: str
    target_probability: float | None = None
    target_margin: float | None = None
    reference_similarity: float | None = None
    engineering_index: float | None = None
    word_match_probability: None = None


def _unit(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.float32)
    if value.ndim != 1 or not np.isfinite(value).all():
        raise ValueError("embedding_invalid")
    norm = float(np.linalg.norm(value))
    if norm <= 1e-8:
        raise ValueError("embedding_zero")
    return value / norm


def build_reference_centroids(
    examples: list[ReferenceExample] | tuple[ReferenceExample, ...],
    *,
    labels: tuple[str, ...],
    maximum_per_target: int = 32,
) -> dict[str, ReferenceCentroid]:
    """MST-006/007: choose at most one deterministic sample per speaker."""
    if maximum_per_target < 1:
        raise ValueError("maximum_per_target_invalid")
    output: dict[str, ReferenceCentroid] = {}
    for label in labels:
        if label == "OTHER":
            continue
        chosen: list[ReferenceExample] = []
        speakers: set[str] = set()
        for item in sorted(examples, key=lambda value: (value.sample_id, value.speaker_pseudonym)):
            if item.label != label or item.speaker_pseudonym in speakers:
                continue
            _unit(item.embedding)
            chosen.append(item)
            speakers.add(item.speaker_pseudonym)
            if len(chosen) == maximum_per_target:
                break
        if chosen:
            centroid = _unit(np.mean(np.stack([_unit(item.embedding) for item in chosen]), axis=0))
            output[label] = ReferenceCentroid(centroid, tuple(item.sample_id for item in chosen), len(speakers))
    return output


def evaluate_development_result(
    target_id: str,
    probabilities: np.ndarray,
    embedding: np.ndarray,
    references: dict[str, np.ndarray],
    calibration: MobileCalibration,
    *,
    vad_ok: bool = True,
) -> DevelopmentEvidence:
    """MST-007: produce review-only evidence while official scoring abstains."""
    if not vad_ok:
        return DevelopmentEvidence("DEV_UNAVAILABLE", "VAD_UNAVAILABLE")
    if target_id not in calibration.labels or target_id == "OTHER" or target_id not in references:
        return DevelopmentEvidence("DEV_UNAVAILABLE", "TARGET_UNAVAILABLE")
    values = np.asarray(probabilities, dtype=np.float64)
    if values.shape != (len(calibration.labels),) or not np.isfinite(values).all() or values.sum() <= 0:
        return DevelopmentEvidence("DEV_UNAVAILABLE", "MODEL_OUTPUT_INVALID")
    try:
        current = _unit(embedding)
        reference = _unit(references[target_id])
    except ValueError:
        return DevelopmentEvidence("DEV_UNAVAILABLE", "REFERENCE_UNAVAILABLE")
    values = values / values.sum()
    target_index = calibration.labels.index(target_id)
    target_probability = float(values[target_index])
    order = np.sort(values)
    margin = float(order[-1] - order[-2])
    similarity = float(np.dot(current, reference))
    similarity_index = (similarity + 1.0) / 2.0
    engineering_index = 0.7 * target_probability + 0.3 * similarity_index
    evidence = dict(
        target_probability=target_probability,
        target_margin=margin,
        reference_similarity=similarity,
        engineering_index=engineering_index,
    )
    if margin < calibration.minimum_margin:
        return DevelopmentEvidence("DEV_UNCERTAIN", "LOW_MARGIN", **evidence)
    if (
        int(values.argmax()) == target_index
        and similarity >= calibration.minimum_similarity
        and engineering_index >= calibration.high_thresholds[target_id]
    ):
        return DevelopmentEvidence("DEV_MATCH", "ADULT_ENGINEERING_MATCH", **evidence)
    if int(values.argmax()) != target_index or engineering_index <= calibration.low_thresholds[target_id]:
        return DevelopmentEvidence("DEV_TRY_AGAIN", "ADULT_ENGINEERING_MISMATCH", **evidence)
    return DevelopmentEvidence("DEV_UNCERTAIN", "ADULT_ENGINEERING_UNCERTAIN", **evidence)


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_bundle(root: Path | str) -> dict[str, object]:
    """MST-006/015: verify every runtime file and v1 architecture binding."""
    directory = Path(root)
    try:
        manifest = json.loads((directory / "bundle.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleIntegrityError("bundle_manifest_invalid") from exc
    if manifest.get("approved_for_child_scoring") is not False:
        raise BundleIntegrityError("child_scoring_must_be_false")
    if (
        manifest.get("bundle_version") == "vm-mobile-student-ta19-v1"
        and manifest.get("architecture_version") != "raw-wave-temporal8-dc-rms-v1"
    ):
        raise BundleIntegrityError("bundle_architecture_mismatch")
    hashes = manifest.get("files")
    if not isinstance(hashes, dict):
        raise BundleIntegrityError("bundle_files_invalid")
    for name in REQUIRED_RUNTIME_FILES:
        path = directory / name
        if not path.is_file():
            raise BundleIntegrityError(f"bundle_file_missing:{name}")
        if _hash(path) != hashes.get(name):
            raise BundleIntegrityError(f"bundle_hash_mismatch:{name}")
    labels = manifest.get("labels")
    if not isinstance(labels, list) or len(labels) < 2 or labels[-1] != "OTHER":
        raise BundleIntegrityError("bundle_labels_invalid")
    return manifest
