"""Immutable word-model bundle verification and loading (DATA-008, OPS-003)."""

from __future__ import annotations

import json
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .calibration import CalibrationArtifact, EvidenceCalibrator
from .canary import CanarySuite, verify_approved_canary_suite
from .classifier import ClassifierArtifact, LinearWordClassifier
from .dtw import ReferenceBank
from .model import NeMoIndicConformerAdapter, sha256_file
from .reference_builder import ReferenceBankBuildError, load_reference_bank_artifact


SHA256_LENGTH = 64
REFERENCE_PREFIX = "reference__"


class ArtifactFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != SHA256_LENGTH or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        return normalized


class ArtifactFiles(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: ArtifactFile
    vocabulary: ArtifactFile
    classifier: ArtifactFile
    reference_bank: ArtifactFile
    calibration: ArtifactFile
    dataset_manifest: ArtifactFile | None = None
    canary_manifest: ArtifactFile | None = None
    canary_run: ArtifactFile | None = None
    vad_config: ArtifactFile | None = None


class CanaryArtifact(ArtifactFile):
    word_id: str = Field(min_length=1)
    target_word: str = Field(min_length=1)


class ReleaseMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    code_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    rollback_bundle_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    signing_input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BundleManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["vaakmitra-word-bundle-1", "vaakmitra-word-bundle-2"]
    deployment_mode: Literal["production", "synthetic_test", "engineering"]
    vocabulary_version: str = Field(min_length=1)
    artifacts: ArtifactFiles
    canary: CanaryArtifact | None = None
    release: ReleaseMetadata | None = None

    @model_validator(mode="after")
    def require_production_canary(self) -> "BundleManifest":
        if self.schema_version == "vaakmitra-word-bundle-1" and self.deployment_mode == "production" and self.canary is None:
            raise ValueError("production bundle requires a canary")
        if self.schema_version == "vaakmitra-word-bundle-2":
            required = (
                self.artifacts.dataset_manifest,
                self.artifacts.canary_manifest,
                self.release,
            )
            if any(item is None for item in required):
                raise ValueError("bundle v2 requires governed dataset, canary, and release metadata")
            if self.deployment_mode == "production" and self.artifacts.canary_run is None:
                raise ValueError("production bundle v2 requires a canary run")
        return self


class BundleVerification(BaseModel):
    model_config = ConfigDict(frozen=True)

    ready: bool
    engineering_ready: bool
    reasons: list[str]
    versions: dict[str, str] = Field(default_factory=dict)
    paths: dict[str, str] = Field(default_factory=dict)


@dataclass(frozen=True)
class LoadedBundle:
    manifest: BundleManifest
    model: NeMoIndicConformerAdapter
    classifier: LinearWordClassifier
    reference_bank: ReferenceBank
    calibrator: EvidenceCalibrator
    vocabulary: dict[str, str]
    canary_path: Path | None


class ArtifactVerificationError(RuntimeError):
    pass


def bundle_signing_input_sha256(manifest: BundleManifest) -> str:
    if manifest.release is None:
        raise ArtifactVerificationError("release_metadata_unavailable")
    payload = {
        "schema_version": manifest.schema_version,
        "deployment_mode": manifest.deployment_mode,
        "vocabulary_version": manifest.vocabulary_version,
        "artifacts": manifest.artifacts.model_dump(mode="json", exclude_none=True),
        "code_commit": manifest.release.code_commit,
        "rollback_bundle_hash": manifest.release.rollback_bundle_hash,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def _bundle_path(root: Path, configured: str) -> Path:
    candidate = Path(configured)
    if candidate.is_absolute():
        raise ArtifactVerificationError("artifact_path_must_be_relative")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ArtifactVerificationError("artifact_path_outside_bundle") from exc
    return resolved


def _scalar_string(archive: np.lib.npyio.NpzFile, key: str) -> str:
    if key not in archive.files:
        raise ArtifactVerificationError(f"{key}_missing")
    value = archive[key]
    if value.shape != ():
        raise ArtifactVerificationError(f"{key}_invalid")
    return str(value.item())


def _load_classifier(path: Path) -> ClassifierArtifact:
    try:
        with np.load(path, allow_pickle=False) as archive:
            labels = tuple(str(item) for item in archive["labels"].tolist())
            return ClassifierArtifact(
                version=_scalar_string(archive, "version"),
                model_hash=_scalar_string(archive, "model_hash"),
                vocabulary_hash=_scalar_string(archive, "vocabulary_hash"),
                labels=labels,
                weights=archive["weights"],
                bias=archive["bias"],
                pooling_schema=(
                    _scalar_string(archive, "pooling_schema")
                    if "pooling_schema" in archive.files
                    else "mean-v1"
                ),
                feature_means=(archive["feature_means"] if "feature_means" in archive.files else None),
                feature_scales=(archive["feature_scales"] if "feature_scales" in archive.files else None),
                temperature=(
                    float(archive["temperature"].item())
                    if "temperature" in archive.files
                    else 1.0
                ),
            )
    except ArtifactVerificationError:
        raise
    except Exception as exc:
        raise ArtifactVerificationError("classifier_payload_invalid") from exc


def _load_reference_bank(path: Path) -> ReferenceBank:
    try:
        with np.load(path, allow_pickle=False) as archive:
            if any(key.startswith("reference_meta__") for key in archive.files):
                return load_reference_bank_artifact(path)
        with np.load(path, allow_pickle=False) as archive:
            references: dict[str, list[np.ndarray]] = {}
            for key in archive.files:
                if not key.startswith(REFERENCE_PREFIX):
                    continue
                remainder = key[len(REFERENCE_PREFIX):]
                word_id, separator, index = remainder.rpartition("__")
                if not separator or not word_id or not index.isdigit():
                    raise ArtifactVerificationError("reference_key_invalid")
                value = np.asarray(archive[key], dtype=np.float32)
                if value.ndim != 2 or value.size == 0 or not np.isfinite(value).all():
                    raise ArtifactVerificationError("reference_embedding_invalid")
                references.setdefault(word_id, []).append(value)
            if not references:
                raise ArtifactVerificationError("reference_bank_empty")
            return ReferenceBank(
                version=_scalar_string(archive, "version"),
                model_hash=_scalar_string(archive, "model_hash"),
                references=references,
                vocabulary_hash=_scalar_string(archive, "vocabulary_hash"),
            )
    except ArtifactVerificationError:
        raise
    except ReferenceBankBuildError as exc:
        raise ArtifactVerificationError(str(exc)) from exc
    except Exception as exc:
        raise ArtifactVerificationError("reference_bank_payload_invalid") from exc


def _inspect_bundle(config_path: Path) -> tuple[BundleManifest, dict[str, Path], dict[str, Any]]:
    try:
        manifest = BundleManifest.model_validate(_read_json(config_path))
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ArtifactVerificationError("bundle_config_invalid") from exc

    root = config_path.parent
    artifact_specs: list[tuple[str, ArtifactFile]] = [
        ("model", manifest.artifacts.model),
        ("vocabulary", manifest.artifacts.vocabulary),
        ("classifier", manifest.artifacts.classifier),
        ("reference_bank", manifest.artifacts.reference_bank),
        ("calibration", manifest.artifacts.calibration),
    ]
    for name, spec in (
        ("dataset_manifest", manifest.artifacts.dataset_manifest),
        ("canary_manifest", manifest.artifacts.canary_manifest),
        ("canary_run", manifest.artifacts.canary_run),
        ("vad_config", manifest.artifacts.vad_config),
    ):
        if spec is not None:
            artifact_specs.append((name, spec))
    if manifest.canary is not None:
        artifact_specs.append(("canary", manifest.canary))
    paths = {name: _bundle_path(root, spec.path) for name, spec in artifact_specs}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ArtifactVerificationError(f"{missing[0]}_unavailable")

    for name, spec in artifact_specs:
        if sha256_file(paths[name]) != spec.sha256:
            raise ArtifactVerificationError(f"{name}_integrity_mismatch")

    try:
        vocabulary_payload = _read_json(paths["vocabulary"])
        vocabulary_version = str(vocabulary_payload["version"])
        words = vocabulary_payload["words"]
        if vocabulary_version != manifest.vocabulary_version or not isinstance(words, dict) or not words:
            raise ArtifactVerificationError("vocabulary_payload_mismatch")
        vocabulary = {str(key): str(value) for key, value in words.items()}
        if manifest.canary is not None and vocabulary.get(manifest.canary.word_id) != manifest.canary.target_word:
            raise ArtifactVerificationError("canary_target_mismatch")
        classifier = _load_classifier(paths["classifier"])
        reference_bank = _load_reference_bank(paths["reference_bank"])
        calibration = CalibrationArtifact.model_validate(_read_json(paths["calibration"]))
    except ArtifactVerificationError:
        raise
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
        raise ArtifactVerificationError("artifact_payload_invalid") from exc

    expected = {
        "model_hash": manifest.artifacts.model.sha256,
        "vocabulary_hash": manifest.artifacts.vocabulary.sha256,
        "classifier_hash": manifest.artifacts.classifier.sha256,
        "reference_bank_hash": manifest.artifacts.reference_bank.sha256,
    }
    checks = {
        "classifier_model_hash_mismatch": classifier.model_hash == expected["model_hash"],
        "classifier_vocabulary_hash_mismatch": classifier.vocabulary_hash == expected["vocabulary_hash"],
        "reference_model_hash_mismatch": reference_bank.model_hash == expected["model_hash"],
        "reference_vocabulary_hash_mismatch": reference_bank.vocabulary_hash == expected["vocabulary_hash"],
        "calibration_model_hash_mismatch": calibration.model_hash == expected["model_hash"],
        "calibration_classifier_hash_mismatch": calibration.classifier_hash == expected["classifier_hash"],
        "calibration_reference_bank_hash_mismatch": calibration.reference_bank_hash == expected["reference_bank_hash"],
        "calibration_vocabulary_hash_mismatch": calibration.vocabulary_hash == expected["vocabulary_hash"],
    }
    for reason, valid in checks.items():
        if not valid:
            raise ArtifactVerificationError(reason)
    canary_human_approved = False
    canary_technical_accepted = False
    if manifest.schema_version == "vaakmitra-word-bundle-2":
        if manifest.release is None or manifest.release.signing_input_sha256 != bundle_signing_input_sha256(manifest):
            raise ArtifactVerificationError("bundle_signing_input_mismatch")
        dataset_hash = manifest.artifacts.dataset_manifest.sha256  # type: ignore[union-attr]
        canary_hash = manifest.artifacts.canary_manifest.sha256  # type: ignore[union-attr]
        if calibration.dataset_manifest_hash != dataset_hash:
            raise ArtifactVerificationError("calibration_dataset_manifest_hash_mismatch")
        try:
            canary_payload = _read_json(paths["canary_manifest"])
            canary_run_payload = _read_json(paths["canary_run"]) if "canary_run" in paths else None
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactVerificationError("canary_payload_invalid") from exc
        if canary_payload.get("vocabulary_hash") != expected["vocabulary_hash"]:
            raise ArtifactVerificationError("canary_vocabulary_hash_mismatch")
        if canary_payload.get("dataset_manifest_hash") != dataset_hash:
            raise ArtifactVerificationError("canary_dataset_manifest_hash_mismatch")
        if canary_run_payload is not None:
            if canary_run_payload.get("suite_hash") != canary_hash:
                raise ArtifactVerificationError("canary_run_suite_hash_mismatch")
            if canary_run_payload.get("technical_accepted") is not True:
                raise ArtifactVerificationError("canary_technical_acceptance_failed")
            canary_technical_accepted = True
        if canary_payload.get("human_approved") is True:
            try:
                suite = CanarySuite.model_validate(canary_payload)
                canary_human_approved = verify_approved_canary_suite(
                    suite, os.environ.get("VAAKMITRA_REVIEW_SIGNING_KEY", ""),
                )
            except (TypeError, ValueError, ValidationError):
                canary_human_approved = False
    elif not calibration.approved:
        raise ArtifactVerificationError("calibration_unapproved")

    return manifest, paths, {
        "vocabulary": vocabulary,
        "classifier": classifier,
        "reference_bank": reference_bank,
        "calibration": calibration,
        "canary_human_approved": canary_human_approved,
        "canary_technical_accepted": canary_technical_accepted,
        "versions": {
            "vocabulary": vocabulary_version,
            "classifier": classifier.version,
            "reference_bank": reference_bank.version,
            "calibration": calibration.version,
        },
    }


def verify_bundle(config_path: Path | str) -> BundleVerification:
    path = Path(config_path)
    if not path.is_file():
        return BundleVerification(
            ready=False,
            engineering_ready=False,
            reasons=["bundle_config_unavailable"],
        )
    try:
        manifest, paths, loaded = _inspect_bundle(path)
    except ArtifactVerificationError as exc:
        return BundleVerification(
            ready=False,
            engineering_ready=False,
            reasons=[str(exc)],
        )
    if manifest.deployment_mode == 'production':
        if (manifest.artifacts.vad_config is None
                or loaded['calibration'].vad_config_hash != manifest.artifacts.vad_config.sha256):
            return BundleVerification(ready=False, engineering_ready=False,
                reasons=['calibration_vad_config_hash_mismatch'])
        from .live_evidence import pipeline_fingerprint
        if loaded['calibration'].live_pipeline_hash != pipeline_fingerprint():
            return BundleVerification(ready=False, engineering_ready=False,
                reasons=['calibration_live_pipeline_hash_mismatch'])
    if manifest.schema_version == "vaakmitra-word-bundle-2":
        reasons: list[str] = []
        if manifest.deployment_mode != "production":
            reasons.append(
                "synthetic_bundle_not_production"
                if manifest.deployment_mode == "synthetic_test"
                else "engineering_bundle_not_production"
            )
        if not loaded["calibration"].approved:
            reasons.append("calibration_unapproved")
        if not loaded["canary_human_approved"]:
            reasons.append("canary_human_unapproved")
        if not loaded["canary_technical_accepted"]:
            reasons.append("canary_technical_unavailable")
        return BundleVerification(
            ready=not reasons,
            engineering_ready=True,
            reasons=reasons,
            versions=loaded["versions"],
            paths={name: str(value) for name, value in paths.items()},
        )
    production = manifest.deployment_mode == "production"
    return BundleVerification(
        ready=production,
        engineering_ready=True,
        reasons=[] if production else ["synthetic_bundle_not_production" if manifest.deployment_mode == "synthetic_test" else "engineering_bundle_not_production"],
        versions=loaded["versions"],
        paths={name: str(value) for name, value in paths.items()},
    )


def load_bundle(config_path: Path | str, *, allow_synthetic: bool = False) -> LoadedBundle:
    path = Path(config_path)
    verification = verify_bundle(path)
    if not verification.ready and not (allow_synthetic and verification.engineering_ready):
        raise ArtifactVerificationError(",".join(verification.reasons) or "bundle_not_ready")
    manifest, paths, loaded = _inspect_bundle(path)
    return LoadedBundle(
        manifest=manifest,
        model=NeMoIndicConformerAdapter(
            model_path=paths["model"],
            expected_sha256=manifest.artifacts.model.sha256,
        ),
        classifier=LinearWordClassifier(loaded["classifier"]),
        reference_bank=loaded["reference_bank"],
        calibrator=EvidenceCalibrator(loaded["calibration"]),
        vocabulary=loaded["vocabulary"],
        canary_path=paths.get("canary"),
    )
