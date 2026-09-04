"""
Tests for the adaptive engine — covers all 10 scenario YAML fixtures
and additional edge cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from asd_backend.adaptive.engine import AdaptiveEngine
from asd_backend.adaptive.policy import TherapistPolicy
from asd_backend.adaptive.schemas import (
    PhonemeScoreInput,
    ScoringResult,
    SessionState,
    SyllableScoreInput,
)

SCENARIOS_DIR = Path(__file__).parent.parent / "asd_backend" / "adaptive" / "scenarios"


def _load_scoring(data: dict | None) -> ScoringResult | None:
    if data is None:
        return None
    return ScoringResult(
        attempt_id=data["attempt_id"],
        model_version=data["model_version"],
        overall_confidence=data["overall_confidence"],
        phoneme_scores=[PhonemeScoreInput(**p) for p in data["phoneme_scores"]],
        syllable_scores=[SyllableScoreInput(**s) for s in data["syllable_scores"]],
    )


def _load_state(data: dict) -> SessionState:
    return SessionState(**data)


# ---------------------------------------------------------------------------
# Parametrised scenario tests from YAML fixtures
# ---------------------------------------------------------------------------

def _scenario_files():
    return sorted(SCENARIOS_DIR.glob("*.yaml"))


@pytest.mark.parametrize("scenario_path", _scenario_files(), ids=lambda p: p.stem)
def test_scenario(scenario_path: Path, default_policy: TherapistPolicy):
    """Load a YAML scenario and assert the engine produces the expected output."""
    scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))

    scoring = _load_scoring(scenario.get("scoring"))
    state = _load_state(scenario["state"])
    expected = scenario["expected"]

    engine = AdaptiveEngine()
    result = engine.decide(scoring, state, default_policy)

    assert result.result == expected["result"], (
        f"[{scenario_path.name}] Expected result={expected['result']!r}, "
        f"got {result.result!r}. Explanation: {result.explanation}"
    )
    assert result.response_intent.value == expected["response_intent"], (
        f"[{scenario_path.name}] Expected intent={expected['response_intent']!r}, "
        f"got {result.response_intent.value!r}"
    )
    assert result.avatar_state.value == expected["avatar_state"]
    assert result.weak_unit == expected["weak_unit"]


# ---------------------------------------------------------------------------
# Edge case: attempts_remaining calculation
# ---------------------------------------------------------------------------

def test_attempts_remaining_decreases(default_policy: TherapistPolicy):
    """attempts_remaining should decrease as attempt_count increases."""
    engine = AdaptiveEngine()
    scoring = ScoringResult(
        attempt_id="ATT-EDGE-01",
        model_version="stub",
        overall_confidence=0.65,  # above low confidence, below overall pass
        phoneme_scores=[
            PhonemeScoreInput(phoneme="a", gop=0.60, confidence=0.65, status="coach"),
        ],
        syllable_scores=[
            SyllableScoreInput(syllable="அம்", score=0.60, status="coach"),
        ],
    )
    for attempt_count in range(3):
        state = SessionState(
            session_id="SES-EDGE",
            exercise_id="TA_AMMA_01",
            target_word="அம்மா",
            attempt_count=attempt_count,
            consecutive_retries=attempt_count,
            session_attempt_count=attempt_count + 1,
            no_response_count=0,
            capture_status="valid",
        )
        result = engine.decide(scoring, state, default_policy)
        expected_remaining = max(0, default_policy.max_retries_per_exercise - attempt_count - 1)
        assert result.attempts_remaining == expected_remaining


# ---------------------------------------------------------------------------
# Privacy invariant: no pronunciation judgement for invalid captures
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("capture_status", ["silence", "clipped", "too_short", "timeout", "cancelled"])
def test_invalid_capture_no_pronunciation_judgement(
    capture_status: str, default_policy: TherapistPolicy
):
    """
    PRIVACY INVARIANT: invalid captures must NEVER receive a pronunciation
    judgement. weak_unit must be null.
    """
    engine = AdaptiveEngine()
    state = SessionState(
        session_id="SES-PRIV",
        exercise_id="TA_AMMA_01",
        target_word="அம்மா",
        attempt_count=0,
        consecutive_retries=0,
        session_attempt_count=1,
        no_response_count=0,
        capture_status=capture_status,
    )
    result = engine.decide(None, state, default_policy)

    assert result.weak_unit is None, (
        f"Privacy violation: capture_status={capture_status!r} produced "
        f"weak_unit={result.weak_unit!r}. Invalid captures must not receive "
        "a pronunciation judgement."
    )
    assert result.result in ("no_response", "retry", "break")


# ---------------------------------------------------------------------------
# Privacy invariant: low confidence capture produces no pronunciation judgement
# ---------------------------------------------------------------------------

def test_low_confidence_no_pronunciation_judgement(default_policy: TherapistPolicy):
    """Low confidence must not produce a weak_unit pronunciation judgement."""
    engine = AdaptiveEngine()
    scoring = ScoringResult(
        attempt_id="ATT-LOW-CONF",
        model_version="stub",
        overall_confidence=0.45,  # below low_confidence_threshold (0.60)
        phoneme_scores=[
            PhonemeScoreInput(phoneme="a", gop=0.40, confidence=0.45, status="retry"),
        ],
        syllable_scores=[
            SyllableScoreInput(syllable="அம்", score=0.40, status="retry"),
        ],
    )
    state = SessionState(
        session_id="SES-PRIV2",
        exercise_id="TA_AMMA_01",
        target_word="அம்மா",
        attempt_count=0,
        consecutive_retries=0,
        session_attempt_count=1,
        no_response_count=0,
        capture_status="valid",
    )
    result = engine.decide(scoring, state, default_policy)
    assert result.weak_unit is None
    assert result.result == "retry"


# ---------------------------------------------------------------------------
# Policy: custom thresholds are respected
# ---------------------------------------------------------------------------

def test_custom_policy_thresholds():
    """Custom policy thresholds override default values."""
    custom_policy = TherapistPolicy(
        policy_version="custom-1.0",
        syllable_pass_score=0.90,  # very strict
        max_retries_per_exercise=1,
    )
    engine = AdaptiveEngine()
    scoring = ScoringResult(
        attempt_id="ATT-CUSTOM",
        model_version="stub",
        overall_confidence=0.85,
        phoneme_scores=[
            PhonemeScoreInput(phoneme="a", gop=0.85, confidence=0.87, status="pass"),
        ],
        syllable_scores=[
            SyllableScoreInput(syllable="அம்", score=0.80, status="pass"),  # passes default but not custom
        ],
    )
    state = SessionState(
        session_id="SES-CUSTOM",
        exercise_id="TA_AMMA_01",
        target_word="அம்மா",
        attempt_count=0,
        consecutive_retries=0,
        session_attempt_count=1,
        no_response_count=0,
        capture_status="valid",
    )
    result = engine.decide(scoring, state, custom_policy)
    # With syllable_pass_score=0.90 and score=0.80, should not pass
    assert result.result != "pass"
