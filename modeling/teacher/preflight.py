"""Pure, credential-safe preflight decisions for the IndicConformer teacher."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EXPECTED_MODEL_ID = "ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large"
MINIMUM_STORAGE_BYTES = 5_000_000_000
PreflightMode = Literal["cpu_smoke", "feature_extract", "full_train"]


class TeacherEnvironmentProbe(BaseModel):
    """Non-secret facts gathered locally or supplied by an authorized access probe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = Field(min_length=1)
    model_revision: str = Field(pattern=r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
    access_authorized: bool
    nemo_available: bool
    torch_available: bool
    cuda_available: bool
    cuda_device_count: int = Field(ge=0)
    free_storage_bytes: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_cuda_consistency(self) -> TeacherEnvironmentProbe:
        if self.cuda_available != (self.cuda_device_count > 0):
            raise ValueError("cuda_available must agree with cuda_device_count")
        return self


class TeacherPreflightReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: PreflightMode
    ready: bool
    code: Literal[
        "cpu_smoke_ready",
        "teacher_feature_extraction_ready",
        "full_training_ready",
        "teacher_model_identity_mismatch",
        "torch_dependency_missing",
        "model_access_not_authorized",
        "nemo_dependency_missing",
        "insufficient_local_storage",
        "gpu_required_for_full_training",
    ]
    evidence_scope: Literal[
        "fixture_encoder_shapes_only", "adult_tamil_teacher", "full_training_environment"
    ]


def _report(
    mode: PreflightMode,
    ready: bool,
    code: str,
    evidence_scope: str,
) -> TeacherPreflightReport:
    return TeacherPreflightReport.model_validate(
        {
            "mode": mode,
            "ready": ready,
            "code": code,
            "evidence_scope": evidence_scope,
        }
    )


def evaluate_teacher_preflight(
    probe: TeacherEnvironmentProbe, *, mode: PreflightMode
) -> TeacherPreflightReport:
    """Return one stable readiness code without receiving or exposing credentials."""

    scope = (
        "fixture_encoder_shapes_only"
        if mode == "cpu_smoke"
        else "adult_tamil_teacher"
        if mode == "feature_extract"
        else "full_training_environment"
    )
    if probe.model_id != EXPECTED_MODEL_ID:
        return _report(mode, False, "teacher_model_identity_mismatch", scope)
    if not probe.torch_available:
        return _report(mode, False, "torch_dependency_missing", scope)
    if mode == "cpu_smoke":
        return _report(mode, True, "cpu_smoke_ready", scope)
    if not probe.access_authorized:
        return _report(mode, False, "model_access_not_authorized", scope)
    if not probe.nemo_available:
        return _report(mode, False, "nemo_dependency_missing", scope)
    if probe.free_storage_bytes < MINIMUM_STORAGE_BYTES:
        return _report(mode, False, "insufficient_local_storage", scope)
    if mode == "feature_extract":
        return _report(mode, True, "teacher_feature_extraction_ready", scope)
    if not probe.cuda_available:
        return _report(mode, False, "gpu_required_for_full_training", scope)
    return _report(mode, True, "full_training_ready", scope)
