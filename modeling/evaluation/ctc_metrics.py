"""Phoneme error metrics that keep proxy and target-user evidence separate."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, TypeVar

_PROXY_POPULATIONS = frozenset({"adult_tamil_proxy", "general_child_proxy"})
_TARGET_POPULATION = "target_user_child"
_Token = TypeVar("_Token")


@dataclass(frozen=True, slots=True)
class EvaluationRecord:
    """One local evaluation item; sequences never enter aggregate reports."""

    utterance_id: str
    reference: tuple[str, ...]
    predicted_tokens: tuple[str, ...]
    blank_token: str
    population: str
    evidence_scope: str
    scorable: bool = True

    def __post_init__(self) -> None:
        if not self.utterance_id.strip():
            raise ValueError("utterance_id must be non-empty")
        if not self.reference or any(not token for token in self.reference):
            raise ValueError("reference must contain non-empty phoneme tokens")
        if any(not token for token in self.predicted_tokens):
            raise ValueError("predicted_tokens must contain non-empty tokens")
        if not self.blank_token:
            raise ValueError("blank_token must be non-empty")
        if self.blank_token in self.reference:
            raise ValueError("reference must not contain the CTC blank token")


@dataclass(frozen=True, slots=True)
class CtcEvaluationReport:
    schema_version: str
    population: str
    evidence_scope: str
    validation_status: str
    record_count: int
    scorable_count: int
    unscorable_count: int
    unscorable_rate: float
    reference_tokens: int
    total_errors: int
    micro_per: float
    macro_per: float
    exact_sequence_accuracy: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def collapse_ctc_tokens(tokens: Sequence[str], blank_token: str) -> tuple[str, ...]:
    """Apply standard CTC repeat collapse followed by blank removal."""

    if not blank_token:
        raise ValueError("blank_token must be non-empty")
    collapsed: list[str] = []
    previous: str | None = None
    for token in tokens:
        if not token:
            raise ValueError("CTC tokens must be non-empty")
        if token != blank_token and token != previous:
            collapsed.append(token)
        previous = token
    return tuple(collapsed)


def edit_distance(reference: Sequence[_Token], hypothesis: Sequence[_Token]) -> int:
    """Return token-level Levenshtein distance using bounded working memory."""

    previous = list(range(len(hypothesis) + 1))
    for reference_index, reference_token in enumerate(reference, start=1):
        current = [reference_index]
        for hypothesis_index, hypothesis_token in enumerate(hypothesis, start=1):
            substitution_cost = 0 if reference_token == hypothesis_token else 1
            current.append(
                min(
                    current[-1] + 1,
                    previous[hypothesis_index] + 1,
                    previous[hypothesis_index - 1] + substitution_cost,
                )
            )
        previous = current
    return previous[-1]


def evaluate_records(records: Sequence[EvaluationRecord]) -> CtcEvaluationReport:
    """Aggregate one frozen population/scope without exposing phoneme sequences."""

    if not records:
        raise ValueError("at least one evaluation record is required")
    populations = {record.population for record in records}
    scopes = {record.evidence_scope for record in records}
    if len(populations) != 1 or len(scopes) != 1:
        raise ValueError("evaluation must contain one population and evidence scope")

    population = next(iter(populations))
    evidence_scope = next(iter(scopes))
    if population not in _PROXY_POPULATIONS | {_TARGET_POPULATION}:
        raise ValueError("unsupported evaluation population")
    if evidence_scope not in {"engineering_proxy", "target_user_validation"}:
        raise ValueError("unsupported evidence scope")
    if evidence_scope == "target_user_validation" and population != _TARGET_POPULATION:
        raise ValueError("target_user_validation requires target_user_child population")
    if population == _TARGET_POPULATION and evidence_scope != "target_user_validation":
        raise ValueError("target_user_child population requires target_user_validation scope")

    utterance_ids = [record.utterance_id for record in records]
    if len(utterance_ids) != len(set(utterance_ids)):
        raise ValueError("utterance_id values must be unique")

    scorable = [record for record in records if record.scorable]
    error_counts: list[int] = []
    reference_counts: list[int] = []
    exact_count = 0
    for record in scorable:
        hypothesis = collapse_ctc_tokens(record.predicted_tokens, record.blank_token)
        errors = edit_distance(record.reference, hypothesis)
        error_counts.append(errors)
        reference_counts.append(len(record.reference))
        exact_count += int(errors == 0)

    scorable_count = len(scorable)
    unscorable_count = len(records) - scorable_count
    total_reference_tokens = sum(reference_counts)
    total_errors = sum(error_counts)
    micro_per = total_errors / total_reference_tokens if total_reference_tokens else 0.0
    macro_per = (
        sum(errors / count for errors, count in zip(error_counts, reference_counts, strict=True))
        / scorable_count
        if scorable_count
        else 0.0
    )
    exact_accuracy = exact_count / scorable_count if scorable_count else 0.0
    unscorable_rate = unscorable_count / len(records)
    metrics = (micro_per, macro_per, exact_accuracy, unscorable_rate)
    if any(not math.isfinite(metric) for metric in metrics):
        raise ValueError("evaluation metrics must be finite")

    return CtcEvaluationReport(
        schema_version="1.0",
        population=population,
        evidence_scope=evidence_scope,
        validation_status=(
            "target_user_validation" if evidence_scope == "target_user_validation" else "engineering_proxy_only"
        ),
        record_count=len(records),
        scorable_count=scorable_count,
        unscorable_count=unscorable_count,
        unscorable_rate=unscorable_rate,
        reference_tokens=total_reference_tokens,
        total_errors=total_errors,
        micro_per=micro_per,
        macro_per=macro_per,
        exact_sequence_accuracy=exact_accuracy,
    )
