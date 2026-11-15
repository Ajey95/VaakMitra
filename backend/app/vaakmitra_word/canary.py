"""Governed release canary manifests and deterministic result checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .model import sha256_file
from .review_exports import sign_review_export, verify_review_export


class CanaryError(RuntimeError):
    """A canary governance or technical acceptance constraint failed."""


@dataclass(frozen=True)
class CanaryInput:
    canary_id: str
    source_sample_id: str
    category: str
    word_id: str
    target_word: str
    audio_path: str
    expected_decision: str
    allowed_reason_codes: tuple[str, ...]
    consent_basis: str
    reviewer_id: str


class CanaryRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    canary_id: str = Field(min_length=1)
    source_sample_id: str = Field(min_length=1)
    category: Literal["positive", "confusable", "audio_quality_negative"]
    word_id: str = Field(pattern=r"^TA_WORD_\d{4}$")
    target_word: str = Field(min_length=1)
    audio_path: str = Field(min_length=1)
    audio_sha256: str
    expected_decision: Literal["PASS", "RETRY", "UNSCORABLE"]
    allowed_reason_codes: tuple[str, ...] = Field(min_length=1)
    consent_basis: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)

    @field_validator("audio_sha256")
    @classmethod
    def valid_audio_hash(cls, value: str) -> str:
        normalized = value.lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("audio hash must be SHA-256")
        return normalized


class CanarySuite(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["vaakmitra-canary-suite-1"]
    vocabulary_hash: str
    dataset_manifest_hash: str
    positive_words: tuple[str, ...]
    categories: tuple[str, ...]
    human_approved: bool = False
    approval_export: dict | None = None
    approval_signature: str | None = None
    records: tuple[CanaryRecord, ...] = Field(min_length=1)

    @field_validator("vocabulary_hash", "dataset_manifest_hash")
    @classmethod
    def valid_hash(cls, value: str) -> str:
        normalized = value.lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("artifact hash must be SHA-256")
        return normalized

    @model_validator(mode="after")
    def unique_canaries(self) -> "CanarySuite":
        identifiers = [record.canary_id for record in self.records]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("canary IDs must be unique")
        return self


class CanaryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    canary_id: str
    actual_decision: str
    actual_reason_code: str
    latency_ms: float = Field(ge=0.0)
    passed: bool


class CanaryRunReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["vaakmitra-canary-run-1"]
    suite_hash: str
    technical_accepted: bool
    human_approved: Literal[False] = False
    p50_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)
    results: tuple[CanaryResult, ...]


def approve_canary_suite(
    candidate: CanarySuite,
    review_export: dict,
    candidate_sha256: str,
    signing_key: str,
) -> CanarySuite:
    """GOV-004: bind qualified human decisions to every exact candidate record."""
    if candidate.human_approved:
        raise CanaryError("canary_candidate_already_approved")
    if not verify_review_export(review_export, signing_key):
        raise CanaryError("canary_review_signature_invalid")
    if (review_export.get("kind") != "canary" or review_export.get("human_approved") is not True
            or review_export.get("manifest_sha256") != candidate_sha256):
        raise CanaryError("canary_review_suite_mismatch")
    rows = review_export.get("items")
    if not isinstance(rows, list) or len(rows) != len(candidate.records):
        raise CanaryError("canary_review_incomplete")
    by_id = {item.get("item_id"): item for item in rows if isinstance(item, dict)}
    if len(by_id) != len(candidate.records):
        raise CanaryError("canary_review_duplicate_or_missing")
    categories = {record.category for record in candidate.records}
    positives = {record.word_id for record in candidate.records if record.category == "positive"}
    if categories != {"positive", "confusable", "audio_quality_negative"} or not set(candidate.positive_words).issubset(positives):
        raise CanaryError("canary_coverage_invalid")
    required_decisions = {"positive": "PASS", "confusable": "RETRY", "audio_quality_negative": "UNSCORABLE"}
    approved_records = []
    for record in candidate.records:
        item = by_id.get(record.canary_id)
        if item is None:
            raise CanaryError("canary_review_missing_item")
        if (item.get("word_id") != record.word_id or item.get("audio_sha256") != record.audio_sha256
                or item.get("observed_sha256") != record.audio_sha256
                or item.get("source_sample_id") != record.source_sample_id
                or item.get("category") != record.category
                or item.get("expected_decision") != record.expected_decision
                or record.expected_decision != required_decisions[record.category]
                or not str(item.get("reviewer_id", "")).strip()):
            raise CanaryError("canary_review_item_mismatch")
        approved_records.append(record.model_copy(update={"reviewer_id": item["reviewer_id"]}))
    approved = candidate.model_copy(update={
        "human_approved": True,
        "records": tuple(approved_records),
        "approval_export": review_export,
    })
    signature = sign_review_export(approved.model_dump(exclude={"approval_signature"}), signing_key)["signature"]
    return approved.model_copy(update={"approval_signature": signature})


def verify_approved_canary_suite(suite: CanarySuite, signing_key: str) -> bool:
    """GOV-004: the production gate requires a signed exact suite, not a boolean."""
    review = suite.approval_export
    if not suite.human_approved or not isinstance(review, dict) or not suite.approval_signature:
        return False
    signed_suite = {**suite.model_dump(exclude={"approval_signature"}), "signature": suite.approval_signature}
    if not verify_review_export(signed_suite, signing_key) or not verify_review_export(review, signing_key):
        return False
    if review.get("kind") != "canary" or review.get("human_approved") is not True:
        return False
    rows = review.get("items")
    if not isinstance(rows, list) or len(rows) != len(suite.records):
        return False
    by_id = {row.get("item_id"): row for row in rows if isinstance(row, dict)}
    if len(by_id) != len(suite.records):
        return False
    for record in suite.records:
        item = by_id.get(record.canary_id)
        if (item is None or item.get("word_id") != record.word_id
                or item.get("source_sample_id") != record.source_sample_id
                or item.get("audio_sha256") != record.audio_sha256
                or item.get("observed_sha256") != record.audio_sha256
                or item.get("category") != record.category
                or item.get("expected_decision") != record.expected_decision
                or item.get("reviewer_id") != record.reviewer_id):
            return False
    return True


def _safe_audio_path(root: Path, configured: str) -> Path:
    candidate = Path(configured)
    if candidate.is_absolute():
        raise CanaryError("canary_audio_path_must_be_relative")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise CanaryError("canary_audio_path_outside_root") from exc
    return resolved


def build_canary_suite(
    inputs: list[CanaryInput] | tuple[CanaryInput, ...],
    *,
    active_words: tuple[str, ...],
    vocabulary_hash: str,
    dataset_manifest_hash: str,
    forbidden_sample_ids: set[str],
    audio_root: Path | str,
) -> CanarySuite:
    if not active_words or len(set(active_words)) != len(active_words):
        raise CanaryError("active_words_invalid")
    root = Path(audio_root)
    records: list[CanaryRecord] = []
    for item in sorted(inputs, key=lambda value: value.canary_id):
        if item.source_sample_id in forbidden_sample_ids:
            raise CanaryError("canary_training_reference_leakage")
        audio_path = _safe_audio_path(root, item.audio_path)
        if not audio_path.is_file():
            raise CanaryError("canary_audio_unavailable")
        try:
            records.append(
                CanaryRecord(
                    **item.__dict__,
                    audio_sha256=sha256_file(audio_path),
                )
            )
        except ValueError as exc:
            raise CanaryError("canary_metadata_invalid") from exc
    positives = tuple(sorted({record.word_id for record in records if record.category == "positive"}))
    missing = sorted(set(active_words) - set(positives))
    if missing:
        raise CanaryError(f"positive_word_coverage_missing:{','.join(missing)}")
    categories = tuple(sorted({record.category for record in records}))
    required_categories = {"positive", "confusable", "audio_quality_negative"}
    if set(categories) != required_categories:
        raise CanaryError("canary_category_coverage_missing")
    return CanarySuite(
        schema_version="vaakmitra-canary-suite-1",
        vocabulary_hash=vocabulary_hash,
        dataset_manifest_hash=dataset_manifest_hash,
        positive_words=positives,
        categories=categories,
        records=tuple(records),
    )


def run_canary_suite(
    suite: CanarySuite,
    *,
    audio_root: Path | str,
    evaluate: Callable[[CanaryRecord, bytes], tuple[str, str, float]],
) -> CanaryRunReport:
    root = Path(audio_root)
    results: list[CanaryResult] = []
    for record in suite.records:
        path = _safe_audio_path(root, record.audio_path)
        if not path.is_file() or sha256_file(path) != record.audio_sha256:
            raise CanaryError("canary_audio_integrity_mismatch")
        decision, reason_code, latency_ms = evaluate(record, path.read_bytes())
        passed = decision == record.expected_decision and reason_code in record.allowed_reason_codes
        results.append(
            CanaryResult(
                canary_id=record.canary_id,
                actual_decision=decision,
                actual_reason_code=reason_code,
                latency_ms=latency_ms,
                passed=passed,
            )
        )
    latencies = np.asarray([result.latency_ms for result in results], dtype=np.float64)
    import hashlib

    suite_hash = hashlib.sha256(
        suite.model_dump_json().encode("utf-8")
    ).hexdigest()
    return CanaryRunReport(
        schema_version="vaakmitra-canary-run-1",
        suite_hash=suite_hash,
        technical_accepted=all(result.passed for result in results),
        p50_latency_ms=float(np.percentile(latencies, 50)),
        p95_latency_ms=float(np.percentile(latencies, 95)),
        results=tuple(results),
    )
