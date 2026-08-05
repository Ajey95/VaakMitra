from __future__ import annotations

import pytest
from modeling.team_mocks.member3_actions import choose_mock_action

from vaakmitra.contracts.scoring import AssessmentResult, PhonemeScore


def _assessment(
    *,
    status: str = "ok",
    scores: tuple[PhonemeScore, ...] = (),
) -> AssessmentResult:
    return AssessmentResult(
        attempt_id="ATT-MOCK-1",
        status=status,  # type: ignore[arg-type]
        model_version="fixture-model-1",
        vocabulary_version="fixture-vocab-1",
        scoring_version="fixture-score-1",
        phoneme_scores=scores,
        overall_confidence=0.9 if status == "ok" else 0.0,
        reason=None if status == "ok" else f"fixture_{status}",
    )


def _score(phoneme: str, gop: float, status: str) -> PhonemeScore:
    return PhonemeScore(
        phoneme=phoneme,
        gop=gop,
        confidence=0.9,
        status=status,  # type: ignore[arg-type]
        start_ms=0.0,
        end_ms=20.0,
    )


def test_mock_action_celebrates_only_when_all_usable_units_pass() -> None:
    action = choose_mock_action(
        _assessment(scores=(_score("a", 0.9, "pass"), _score("m", 0.85, "pass")))
    )

    assert action.response_intent == "CELEBRATE_AND_CONTINUE"
    assert action.weak_unit is None
    assert action.production_eligible is False
    assert action.clinical_validity is False


def test_mock_action_targets_lowest_scoring_coach_unit() -> None:
    action = choose_mock_action(
        _assessment(
            scores=(
                _score("a", 0.9, "pass"),
                _score("m", 0.6, "coach"),
                _score("a\u02d0", 0.4, "coach"),
            )
        )
    )

    assert action.response_intent == "ENCOURAGE_TARGETED_PRACTICE"
    assert action.weak_unit == "a\u02d0"


def test_mock_action_does_not_celebrate_empty_ok_evidence() -> None:
    action = choose_mock_action(_assessment())

    assert action.response_intent == "REQUEST_NEUTRAL_RECAPTURE"
    assert action.weak_unit is None


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("retry", "ENCOURAGE_NEUTRAL_RETRY"),
        ("unscorable", "REQUEST_NEUTRAL_RECAPTURE"),
        ("error", "PAUSE_AND_REPORT_TECHNICAL_ERROR"),
    ],
)
def test_mock_action_preserves_neutral_failures(status: str, expected: str) -> None:
    action = choose_mock_action(_assessment(status=status))

    assert action.response_intent == expected
    assert action.weak_unit is None
    assert action.evidence_scope == "mock_dependency_integration"
    assert action.clinical_validity is False
