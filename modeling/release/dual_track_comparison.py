"""Deterministic full-reference versus edge-student promotion comparison."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from modeling.evaluation.promotion import PromotionReport


class ComparisonCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    model_id: str = Field(min_length=1)
    role: Literal["full_reference", "student", "historical_proxy"]
    adult_tamil_per: float | None = Field(default=None, ge=0.0)
    model_size_bytes: int | None = Field(default=None, gt=0)
    exportable: bool
    promotion: PromotionReport | None

    @model_validator(mode="after")
    def validate_promotion_binding(self) -> Self:
        if self.role == "historical_proxy":
            if self.promotion is not None:
                raise ValueError("historical proxy cannot carry a promotion decision")
            return self
        if self.promotion is None or self.promotion.model_id != self.model_id:
            raise ValueError("candidate promotion must bind the same model_id")
        if self.promotion.track != self.role:
            raise ValueError("candidate role must match promotion track")
        return self


class CandidateComparisonSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str
    role: Literal["full_reference", "student", "historical_proxy"]
    adult_tamil_per: float | None
    model_size_bytes: int | None
    exportable: bool
    promotion_status: Literal["promoted", "not_promoted", "not_applicable"]
    passed_gates: int = Field(ge=0)
    failed_gates: int = Field(ge=0)
    not_measured_gates: int = Field(ge=0)


class DualTrackComparisonReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    candidates: tuple[CandidateComparisonSummary, ...]
    reference_model_id: str | None
    selected_edge_model_id: str | None
    edge_selection_status: Literal[
        "promoted_student_selected", "no_student_passed_all_gates"
    ]
    outstanding_work: tuple[str, ...]
    evidence_scope: Literal["engineering_proxy"] = "engineering_proxy"
    clinical_validity_claimed: Literal[False] = False

    def digest(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"), separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        result = self.model_dump(mode="json")
        result["comparison_sha256"] = self.digest()
        return result


def _summary(candidate: ComparisonCandidate) -> CandidateComparisonSummary:
    if candidate.promotion is None:
        return CandidateComparisonSummary(
            model_id=candidate.model_id,
            role=candidate.role,
            adult_tamil_per=candidate.adult_tamil_per,
            model_size_bytes=candidate.model_size_bytes,
            exportable=candidate.exportable,
            promotion_status="not_applicable",
            passed_gates=0,
            failed_gates=0,
            not_measured_gates=0,
        )
    statuses = [gate.status for gate in candidate.promotion.gates]
    return CandidateComparisonSummary(
        model_id=candidate.model_id,
        role=candidate.role,
        adult_tamil_per=candidate.adult_tamil_per,
        model_size_bytes=candidate.model_size_bytes,
        exportable=candidate.exportable,
        promotion_status="promoted" if candidate.promotion.promoted else "not_promoted",
        passed_gates=statuses.count("pass"),
        failed_gates=statuses.count("fail"),
        not_measured_gates=statuses.count("not_measured"),
    )


def compare_dual_tracks(
    candidates: Sequence[ComparisonCandidate],
) -> DualTrackComparisonReport:
    """Select only fully promoted models; quality alone cannot bypass edge gates."""

    if not candidates:
        raise ValueError("dual-track comparison requires candidates")
    identifiers = [candidate.model_id for candidate in candidates]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("comparison candidate model identifiers must be unique")
    promoted_full = [
        candidate
        for candidate in candidates
        if candidate.role == "full_reference"
        and candidate.promotion is not None
        and candidate.promotion.promoted
        and candidate.adult_tamil_per is not None
    ]
    reference = min(
        promoted_full,
        key=lambda item: (item.adult_tamil_per or float("inf"), item.model_id),
        default=None,
    )
    eligible_students = [
        candidate
        for candidate in candidates
        if candidate.role == "student"
        and candidate.promotion is not None
        and candidate.promotion.promoted
        and candidate.exportable
        and candidate.adult_tamil_per is not None
        and candidate.model_size_bytes is not None
    ]
    selected = min(
        eligible_students,
        key=lambda item: (
            item.adult_tamil_per or float("inf"),
            item.model_size_bytes or 2**63,
            item.model_id,
        ),
        default=None,
    )
    outstanding: list[str] = []
    if reference is None:
        outstanding.append("missing promoted full-reference GPU evidence")
    if selected is None:
        outstanding.append("no student passed every edge promotion gate")
    student_physical_pass = any(
        candidate.role == "student"
        and candidate.promotion is not None
        and any(
            gate.name == "physical_android_p95_ms" and gate.status == "pass"
            for gate in candidate.promotion.gates
        )
        for candidate in candidates
    )
    if not student_physical_pass:
        outstanding.append("missing physical Android benchmark")
    outstanding.append("missing therapist-labelled child validation")

    return DualTrackComparisonReport(
        candidates=tuple(
            _summary(candidate) for candidate in sorted(candidates, key=lambda item: item.model_id)
        ),
        reference_model_id=reference.model_id if reference is not None else None,
        selected_edge_model_id=selected.model_id if selected is not None else None,
        edge_selection_status=(
            "promoted_student_selected"
            if selected is not None
            else "no_student_passed_all_gates"
        ),
        outstanding_work=tuple(outstanding),
    )
