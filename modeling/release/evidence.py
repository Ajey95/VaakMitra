"""Hash-linked release evidence with explicit clinical and target-device gates."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from modeling.artifacts import describe_artifact

EvidenceKind = Literal[
    "model",
    "vocabulary",
    "corpus",
    "evaluation",
    "calibration",
    "comparison",
    "benchmark",
]

_REQUIRED_KINDS = frozenset(
    {
        "model",
        "vocabulary",
        "corpus",
        "evaluation",
        "calibration",
        "comparison",
        "benchmark",
    }
)
_EMBEDDED_SCOPE_FIELDS = {
    "corpus": "evidence_scope",
    "evaluation": "evidence_scope",
    "calibration": "calibration_status",
    "benchmark": "evidence_scope",
}


class EvidenceInput(BaseModel):
    """One local artifact and the evidence meaning claimed for it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: EvidenceKind
    path: Path
    evidence_scope: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class ArtifactEvidence:
    kind: str
    filename: str
    size_bytes: int
    sha256: str
    evidence_scope: str


@dataclass(frozen=True, slots=True)
class ReleaseEvidence:
    schema_version: str
    release_status: str
    validation_label: str
    artifacts: tuple[ArtifactEvidence, ...]
    limitations: tuple[str, ...]
    evidence_digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _embedded_scope(item: EvidenceInput) -> str | None:
    field = _EMBEDDED_SCOPE_FIELDS.get(item.kind)
    if field is None:
        return None
    try:
        payload = json.loads(item.path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{item.kind} evidence must be valid JSON") from error
    if not isinstance(payload, dict) or not isinstance(payload.get(field), str):
        raise TypeError(f"{item.kind} evidence must contain string field {field}")
    return str(payload[field])


def _validate_required_kinds(inputs: Sequence[EvidenceInput]) -> None:
    counts = Counter(item.kind for item in inputs)
    if set(counts) != _REQUIRED_KINDS or any(count != 1 for count in counts.values()):
        raise ValueError("release evidence requires exactly one artifact for every required kind")


def _canonical_digest(
    status: str,
    artifacts: Sequence[ArtifactEvidence],
    limitations: Sequence[str],
) -> str:
    payload = {
        "release_status": status,
        "artifacts": [asdict(artifact) for artifact in artifacts],
        "limitations": list(limitations),
    }
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def assemble_release_evidence(
    inputs: Sequence[EvidenceInput],
    *,
    requested_status: str,
) -> ReleaseEvidence:
    """Assemble aggregate evidence and block unsupported validation claims."""

    if requested_status not in {"technical_prototype", "target_device_validated"}:
        raise ValueError("requested_status must be technical_prototype or target_device_validated")
    _validate_required_kinds(inputs)

    scopes: dict[str, str] = {}
    artifacts: list[ArtifactEvidence] = []
    for item in inputs:
        try:
            record = describe_artifact(item.path)
        except ValueError as error:
            raise ValueError(f"{item.kind} artifact must be a non-empty file") from error
        embedded_scope = _embedded_scope(item)
        if embedded_scope is not None and embedded_scope != item.evidence_scope:
            raise ValueError(
                f"{item.kind} declared scope does not match embedded evidence scope"
            )
        scopes[item.kind] = item.evidence_scope
        artifacts.append(
            ArtifactEvidence(
                kind=item.kind,
                filename=item.path.name,
                size_bytes=record.size_bytes,
                sha256=record.sha256,
                evidence_scope=item.evidence_scope,
            )
        )
    artifacts.sort(key=lambda artifact: artifact.kind)

    has_target_user_evidence = (
        scopes["corpus"] == "target_user_validation"
        and scopes["evaluation"] == "target_user_validation"
        and scopes["calibration"] == "therapist_calibrated"
    )
    has_target_device_evidence = scopes["benchmark"] == "target_device"
    if scopes["model"] not in {
        "synthetic_fixture_model",
        "trained_proxy_tamil_phoneme_model",
        "approved_tamil_phoneme_model",
    }:
        raise ValueError("model evidence scope is unsupported")
    has_trained_tamil_model = scopes["model"] in {
        "trained_proxy_tamil_phoneme_model",
        "approved_tamil_phoneme_model",
    }

    if requested_status == "target_device_validated":
        if not has_target_device_evidence:
            raise ValueError("target_device_validated requires an actual target_device benchmark")
        if (
            scopes["corpus"] != "target_user_validation"
            or scopes["evaluation"] != "target_user_validation"
        ):
            raise ValueError(
                "target_device_validated requires corpus and evaluation target_user_validation"
            )
        if scopes["calibration"] != "therapist_calibrated":
            raise ValueError("target_device_validated requires therapist_calibrated evidence")
        if scopes["model"] != "approved_tamil_phoneme_model":
            raise ValueError(
                "target_device_validated requires approved_tamil_phoneme_model evidence"
            )

    limitations: list[str] = []
    if not has_target_user_evidence:
        limitations.append("no therapist-labelled target-user evidence")
    if not has_target_device_evidence:
        limitations.append("no actual target-device benchmark")
    if not has_trained_tamil_model:
        limitations.append("no trained Tamil phoneme CTC model")

    artifact_tuple = tuple(artifacts)
    limitation_tuple = tuple(limitations)
    return ReleaseEvidence(
        schema_version="1.0",
        release_status=requested_status,
        validation_label=(
            "external_target_evidence_present"
            if requested_status == "target_device_validated"
            else "engineering_evidence_only"
        ),
        artifacts=artifact_tuple,
        limitations=limitation_tuple,
        evidence_digest=_canonical_digest(requested_status, artifact_tuple, limitation_tuple),
    )
