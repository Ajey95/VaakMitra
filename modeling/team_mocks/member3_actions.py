"""Deterministic Member 3 action mock for contract integration tests only."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from vaakmitra.contracts.scoring import AssessmentResult

ResponseIntent = Literal[
    "CELEBRATE_AND_CONTINUE",
    "ENCOURAGE_TARGETED_PRACTICE",
    "ENCOURAGE_NEUTRAL_RETRY",
    "REQUEST_NEUTRAL_RECAPTURE",
    "PAUSE_AND_REPORT_TECHNICAL_ERROR",
]


@dataclass(frozen=True, slots=True)
class MockActionEnvelope:
    """Action plus evidence labels that prevent clinical interpretation."""

    dependency: str
    implementation: str
    evidence_scope: str
    production_eligible: bool
    clinical_validity: bool
    response_intent: ResponseIntent
    weak_unit: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _action(
    response_intent: ResponseIntent,
    *,
    weak_unit: str | None = None,
) -> MockActionEnvelope:
    return MockActionEnvelope(
        dependency="member3",
        implementation="deterministic_mock",
        evidence_scope="mock_dependency_integration",
        production_eligible=False,
        clinical_validity=False,
        response_intent=response_intent,
        weak_unit=weak_unit,
    )


def choose_mock_action(result: AssessmentResult) -> MockActionEnvelope:
    """Map Member 2 evidence to a non-production deterministic action."""

    if result.status == "error":
        return _action("PAUSE_AND_REPORT_TECHNICAL_ERROR")
    if result.status == "unscorable":
        return _action("REQUEST_NEUTRAL_RECAPTURE")
    if result.status == "retry":
        return _action("ENCOURAGE_NEUTRAL_RETRY")
    if not result.phoneme_scores:
        return _action("REQUEST_NEUTRAL_RECAPTURE")

    coached = tuple(score for score in result.phoneme_scores if score.status == "coach")
    if coached:
        weakest = min(coached, key=lambda score: (score.gop, score.phoneme))
        return _action(
            "ENCOURAGE_TARGETED_PRACTICE",
            weak_unit=weakest.phoneme,
        )
    if any(score.status != "pass" for score in result.phoneme_scores):
        return _action("REQUEST_NEUTRAL_RECAPTURE")
    return _action("CELEBRATE_AND_CONTINUE")
