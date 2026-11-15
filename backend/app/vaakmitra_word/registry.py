"""Artifact registry with separate engineering and production readiness (MOD-008)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .artifacts import BundleVerification, LoadedBundle, load_bundle, verify_bundle
from .assessment import AssessmentContext, WordAssessmentService
from .contracts import Decision, ModelReadiness
from .model import AcousticModel, ModelCapabilityError, NeMoIndicConformerAdapter, sha256_file
from .policy import PolicyMode, SafeAdaptivePolicy, TherapistConstraints


@dataclass(frozen=True)
class ArtifactSettings:
    model_path: Path
    model_sha256: str
    classifier_path: Path
    reference_bank_path: Path
    calibration_path: Path


class ServiceRegistry:
    def __init__(self, settings: ArtifactSettings, *, model: AcousticModel | None = None) -> None:
        self.settings = settings
        self.model: AcousticModel = model or NeMoIndicConformerAdapter(
            model_path=settings.model_path,
            expected_sha256=settings.model_sha256,
        )

    def scoring_readiness(self) -> ModelReadiness:
        reasons: list[str] = []
        model_exists = self.settings.model_path.is_file()
        is_test_double = bool(getattr(self.model, "is_test_double", False))
        if is_test_double:
            reasons.append("test_model_not_production")
        elif not model_exists:
            reasons.append("model_unavailable")
        elif sha256_file(self.settings.model_path) != self.settings.model_sha256.lower():
            reasons.append("model_integrity_mismatch")

        for name, path in (
            ("classifier_unavailable", self.settings.classifier_path),
            ("reference_bank_unavailable", self.settings.reference_bank_path),
            ("calibration_unavailable", self.settings.calibration_path),
        ):
            if not path.is_file():
                reasons.append(name)
        return ModelReadiness(
            ready=not reasons,
            engineering_ready=is_test_double and bool(getattr(self.model, "ready", False)),
            reasons=reasons,
            model_version=getattr(self.model, "model_version", "unavailable"),
        )


class BundleRuntimeRegistry:
    """Reports verified-bundle and loaded-runtime state without overstating readiness."""

    def __init__(
        self,
        verification: BundleVerification,
        *,
        bundle: LoadedBundle | None = None,
        runtime_reason: str | None = None,
    ) -> None:
        self.verification = verification
        self.bundle = bundle
        self.runtime_reason = runtime_reason

    def scoring_readiness(self) -> ModelReadiness:
        reasons = list(self.verification.reasons)
        if self.verification.ready and self.runtime_reason:
            reasons.append(self.runtime_reason)
        if self.verification.ready and self.bundle is not None and not self.bundle.model.ready:
            reasons.append("model_runtime_not_loaded")
        versions = self.verification.versions
        return ModelReadiness(
            ready=self.verification.ready and self.bundle is not None and not reasons and self.bundle.model.ready,
            engineering_ready=self.verification.engineering_ready,
            reasons=list(dict.fromkeys(reasons)),
            model_version=(
                self.bundle.model.model_version if self.bundle is not None else "unavailable"
            ),
            classifier_version=versions.get("classifier", "unavailable"),
            reference_bank_version=versions.get("reference_bank", "unavailable"),
            calibration_version=versions.get("calibration", "unavailable"),
        )


def build_runtime(config_path: Path | str) -> tuple[BundleRuntimeRegistry, WordAssessmentService | None]:
    """Build the production service only from a verified, non-synthetic bundle."""
    verification = verify_bundle(config_path)
    if not verification.ready:
        return BundleRuntimeRegistry(verification), None
    try:
        bundle = load_bundle(config_path)
        bundle.model.load()
    except ModelCapabilityError as exc:
        reason = str(exc).split(":", 1)[0]
        return BundleRuntimeRegistry(verification, runtime_reason=reason), None
    except Exception:
        return BundleRuntimeRegistry(verification, runtime_reason="artifact_load_failed"), None
    service = WordAssessmentService(
        model=bundle.model,
        classifier=bundle.classifier,
        reference_bank=bundle.reference_bank,
        calibrator=bundle.calibrator,
        policy=SafeAdaptivePolicy(PolicyMode.DETERMINISTIC),
    )
    if "vad_config" in verification.paths:
        try:
            from .vad import OnnxVad
            service.vad = OnnxVad.from_config(verification.paths["vad_config"])
        except Exception:
            return BundleRuntimeRegistry(verification, bundle=bundle, runtime_reason="vad_runtime_unavailable"), None
    if not service.production_vad_ready:
        return BundleRuntimeRegistry(verification, bundle=bundle, runtime_reason="vad_runtime_unavailable"), None
    canary = bundle.manifest.canary
    if canary is None or bundle.canary_path is None:
        return BundleRuntimeRegistry(
            verification,
            bundle=bundle,
            runtime_reason="model_canary_unavailable",
        ), None
    try:
        canary_result = service.assess(
            bundle.canary_path.read_bytes(),
            AssessmentContext(
                session_id="SYSTEM_CANARY",
                attempt_id="SYSTEM_CANARY",
                word_id=canary.word_id,
                target_word=canary.target_word,
                attempt_count=0,
                therapist_constraints=TherapistConstraints(
                    allowed_actions=("next_word", "break", "safe_end"),
                    next_exercise_id=canary.word_id,
                ),
            ),
        )
    except Exception:
        return BundleRuntimeRegistry(
            verification,
            bundle=bundle,
            runtime_reason="model_canary_failed",
        ), None
    if canary_result.decision is not Decision.PASS:
        return BundleRuntimeRegistry(
            verification,
            bundle=bundle,
            runtime_reason="model_canary_failed",
        ), None
    registry = BundleRuntimeRegistry(verification, bundle=bundle)
    return registry, service


def build_technical_canary_runtime(config_path: Path | str) -> tuple[BundleRuntimeRegistry, WordAssessmentService | None]:
    """GOV-004: evaluate a staged suite without pretending release readiness.

    This bypasses only the *completed canary-run* prerequisite that a new
    technical run is meant to produce. Artifact integrity, approved
    calibration, VAD and live-pipeline binding remain mandatory.
    """
    verification = verify_bundle(config_path)
    if not verification.engineering_ready:
        return BundleRuntimeRegistry(verification), None
    try:
        bundle = load_bundle(config_path, allow_synthetic=True)
        bundle.model.load()
        service = WordAssessmentService(
            model=bundle.model, classifier=bundle.classifier,
            reference_bank=bundle.reference_bank, calibrator=bundle.calibrator,
            policy=SafeAdaptivePolicy(PolicyMode.DETERMINISTIC),
        )
        if "vad_config" not in verification.paths:
            return BundleRuntimeRegistry(verification, bundle=bundle, runtime_reason="vad_runtime_unavailable"), None
        from .vad import OnnxVad
        service.vad = OnnxVad.from_config(verification.paths["vad_config"])
        if not bundle.calibrator.ready:
            return BundleRuntimeRegistry(verification, bundle=bundle, runtime_reason="calibration_unapproved"), None
        if not service.production_vad_ready:
            return BundleRuntimeRegistry(verification, bundle=bundle, runtime_reason="vad_runtime_unavailable"), None
        if not service.live_pipeline_ready:
            return BundleRuntimeRegistry(verification, bundle=bundle, runtime_reason="calibration_live_pipeline_hash_mismatch"), None
        return BundleRuntimeRegistry(verification, bundle=bundle), service
    except ModelCapabilityError as exc:
        return BundleRuntimeRegistry(verification, runtime_reason=str(exc).split(":", 1)[0]), None
    except Exception:
        return BundleRuntimeRegistry(verification, runtime_reason="artifact_load_failed"), None
