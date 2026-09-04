"""
Adaptive Exercise and Dialogue Decision Engine — M3.2

Converts GOP/confidence results + session state + therapist policy
into an auditable, approved response intent and next exercise decision.

Design rules
------------
- Pure function logic: no I/O, no ML, no clinical diagnosis.
- Every decision has an explanation string for audit.
- A low-confidence or invalid capture NEVER receives a negative
  pronunciation judgement — it always maps to a neutral retry intent.
- This module does not generate unrestricted clinical text.
"""

from __future__ import annotations

import structlog

from asd_backend.adaptive.policy import TherapistPolicy
from asd_backend.adaptive.schemas import (
    AvatarState,
    DecisionResult,
    ResponseIntent,
    ScoringResult,
    SessionState,
)

log = structlog.get_logger(__name__)


class AdaptiveEngine:
    """
    Rules-based adaptive decision engine.

    Instantiate once per session (or share across sessions — it is stateless).
    All state lives in SessionState which the orchestrator manages.
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def decide(
        self,
        scoring: ScoringResult | None,
        state: SessionState,
        policy: TherapistPolicy,
    ) -> DecisionResult:
        """
        Produce a DecisionResult for one child attempt.

        Parameters
        ----------
        scoring:
            GOP/confidence output from Member 2, or None for invalid captures.
        state:
            Current session state managed by the orchestrator.
        policy:
            Active therapist policy.

        Returns
        -------
        DecisionResult
            Fully populated decision including response intent, next exercise,
            avatar state, and audit explanation.
        """
        log.debug(
            "adaptive_engine.decide",
            attempt_id=scoring.attempt_id if scoring else "N/A",
            capture_status=state.capture_status,
            attempt_count=state.attempt_count,
        )

        # ── 1. Fatigue break — session-level limit ────────────────────────────
        if state.session_attempt_count >= policy.max_attempts_per_session:
            return self._make_result(
                attempt_id=scoring.attempt_id if scoring else "N/A",
                result="break",
                weak_unit=None,
                intent=ResponseIntent.OFFER_BREAK,
                avatar=AvatarState.NEUTRAL,
                next_exercise_id=state.next_exercise_id or state.exercise_id,
                attempts_remaining=0,
                explanation=(
                    f"Session attempt limit reached "
                    f"({state.session_attempt_count}/{policy.max_attempts_per_session}). "
                    "Fatigue break triggered."
                ),
                policy=policy,
            )

        # ── 2. No-response ────────────────────────────────────────────────────
        if state.capture_status in ("silence", "timeout"):
            if state.no_response_count >= policy.max_no_response_before_prompt:
                intent = ResponseIntent.PROMPT_LOUDER
                explanation = (
                    f"No response detected {state.no_response_count} times. "
                    "Switching to louder prompt intent."
                )
            else:
                intent = ResponseIntent.NO_RESPONSE_PROMPT
                explanation = (
                    f"No speech detected (status={state.capture_status}). "
                    "Neutral wait prompt, no pronunciation judgement."
                )
            return self._make_result(
                attempt_id=scoring.attempt_id if scoring else "N/A",
                result="no_response",
                weak_unit=None,
                intent=intent,
                avatar=AvatarState.WAIT,
                next_exercise_id=state.exercise_id,  # repeat same
                attempts_remaining=_remaining(state, policy),
                explanation=explanation,
                policy=policy,
            )

        # ── 3. Invalid capture (clipping, too short, cancelled) ───────────────
        if state.capture_status != "valid" or scoring is None:
            return self._make_result(
                attempt_id=scoring.attempt_id if scoring else "N/A",
                result="retry",
                weak_unit=None,
                intent=ResponseIntent.ENCOURAGE_RETRY,
                avatar=AvatarState.NEUTRAL,
                next_exercise_id=state.exercise_id,
                attempts_remaining=_remaining(state, policy),
                explanation=(
                    f"Capture invalid (status={state.capture_status}). "
                    "Neutral retry — no pronunciation judgement issued."
                ),
                policy=policy,
            )

        # ── 4. Low overall confidence — cannot score ──────────────────────────
        if scoring.overall_confidence < policy.low_confidence_threshold:
            return self._make_result(
                attempt_id=scoring.attempt_id,
                result="retry",
                weak_unit=None,
                intent=ResponseIntent.LOW_CONFIDENCE_RETRY,
                avatar=AvatarState.NEUTRAL,
                next_exercise_id=state.exercise_id,
                attempts_remaining=_remaining(state, policy),
                explanation=(
                    f"Overall confidence {scoring.overall_confidence:.2f} below "
                    f"threshold {policy.low_confidence_threshold:.2f}. "
                    "Cannot score — neutral retry, no pronunciation judgement."
                ),
                policy=policy,
            )

        # ── 5. Max retries reached for this exercise ──────────────────────────
        if state.attempt_count >= policy.max_retries_per_exercise:
            return self._make_result(
                attempt_id=scoring.attempt_id,
                result="break",
                weak_unit=None,
                intent=ResponseIntent.OFFER_BREAK,
                avatar=AvatarState.NEUTRAL,
                next_exercise_id=state.next_exercise_id or state.exercise_id,
                attempts_remaining=0,
                explanation=(
                    f"Max retries per exercise reached "
                    f"({state.attempt_count}/{policy.max_retries_per_exercise}). "
                    "Moving to next exercise or break."
                ),
                policy=policy,
            )

        # ── 6. Evaluate syllable scores ───────────────────────────────────────
        failing_syllables = [
            s for s in scoring.syllable_scores
            if s.score < policy.syllable_pass_score
        ]

        # All syllables pass
        if not failing_syllables:
            return self._make_result(
                attempt_id=scoring.attempt_id,
                result="pass",
                weak_unit=None,
                intent=ResponseIntent.CELEBRATE_PASS,
                avatar=AvatarState.CELEBRATE,
                next_exercise_id=state.next_exercise_id or state.exercise_id,
                attempts_remaining=_remaining(state, policy),
                explanation=(
                    f"All {len(scoring.syllable_scores)} syllables passed "
                    f"(threshold={policy.syllable_pass_score:.2f}). "
                    f"Overall confidence={scoring.overall_confidence:.2f}."
                ),
                policy=policy,
            )

        # One or more syllables need coaching — pick the weakest
        weakest = min(failing_syllables, key=lambda s: s.score)

        # If confidence is in the acceptable range → targeted coaching
        if scoring.overall_confidence >= policy.overall_pass_confidence:
            return self._make_result(
                attempt_id=scoring.attempt_id,
                result="targeted_coaching",
                weak_unit=weakest.syllable,
                intent=ResponseIntent.ENCOURAGE_REPEAT_SYLLABLE,
                avatar=AvatarState.COACH,
                next_exercise_id=_syllable_exercise_id(state.exercise_id, weakest.syllable),
                attempts_remaining=_remaining(state, policy),
                explanation=(
                    f"Weakest syllable '{weakest.syllable}' scored {weakest.score:.2f} "
                    f"(threshold={policy.syllable_pass_score:.2f}). "
                    f"Overall confidence={scoring.overall_confidence:.2f}. "
                    "Targeting specific syllable coaching."
                ),
                policy=policy,
            )

        # Confidence is moderate — encourage a general retry
        return self._make_result(
            attempt_id=scoring.attempt_id,
            result="retry",
            weak_unit=weakest.syllable,
            intent=ResponseIntent.ENCOURAGE_RETRY,
            avatar=AvatarState.COACH,
            next_exercise_id=state.exercise_id,
            attempts_remaining=_remaining(state, policy),
            explanation=(
                f"Syllable '{weakest.syllable}' failed (score={weakest.score:.2f}) and "
                f"confidence is moderate ({scoring.overall_confidence:.2f}). "
                "General retry encouraged."
            ),
            policy=policy,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _make_result(
        attempt_id: str,
        result: str,
        weak_unit: str | None,
        intent: ResponseIntent,
        avatar: AvatarState,
        next_exercise_id: str,
        attempts_remaining: int,
        explanation: str,
        policy: TherapistPolicy,
    ) -> DecisionResult:
        return DecisionResult(
            attempt_id=attempt_id,
            result=result,
            weak_unit=weak_unit,
            response_intent=intent,
            avatar_state=avatar,
            next_exercise_id=next_exercise_id,
            attempts_remaining=attempts_remaining,
            explanation=explanation,
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _remaining(state: SessionState, policy: TherapistPolicy) -> int:
    """Remaining attempts for the current exercise."""
    used = state.attempt_count + 1  # +1 for the current attempt
    return max(0, policy.max_retries_per_exercise - used)


def _syllable_exercise_id(exercise_id: str, syllable: str) -> str:
    """
    Derive a syllable-focused sub-exercise ID from the parent exercise.
    Format: TA_SYL_<syllable_romanised> derived from parent.
    The actual mapping is handled by the exercise plan; this produces a
    deterministic lookup key.
    """
    # Strip non-ASCII for the ID suffix (keep a safe ASCII representation)
    safe = "".join(c for c in syllable if c.isascii() and c.isalpha()).upper()
    if not safe:
        # For Tamil Unicode syllables, use a hash prefix
        safe = f"U{abs(hash(syllable)) % 10000:04d}"
    return f"TA_SYL_{safe}"
