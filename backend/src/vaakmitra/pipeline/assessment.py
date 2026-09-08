"""Member 2 orchestration without retaining audio or implementing forced alignment."""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

from vaakmitra.acoustic.base import AcousticModelRuntime
from vaakmitra.contracts.acoustic import AcousticOutput
from vaakmitra.contracts.alignment import AlignmentResult, SyllableDefinition
from vaakmitra.contracts.scoring import AssessmentResult, AssessmentStatus, PhonemeScore
from vaakmitra.ctc.probabilities import validate_log_probabilities
from vaakmitra.ctc.vocabulary import PhonemeVocabulary
from vaakmitra.scoring.confidence import ScoringConfig
from vaakmitra.scoring.gop import UnscorableEvidenceError, score_aligned_phonemes
from vaakmitra.scoring.syllables import aggregate_syllables


class AcousticInferenceError(RuntimeError):
    """Neutral inference failure that never exposes model paths or provider details."""


class AssessmentPipeline:
    """Expose probabilities for Member 1, then score Member 1's alignment."""

    def __init__(
        self,
        *,
        runtime: AcousticModelRuntime,
        vocabulary: PhonemeVocabulary,
        config: ScoringConfig,
    ) -> None:
        self._runtime = runtime
        self._vocabulary = vocabulary
        self._config = config

    def infer(
        self,
        audio: npt.NDArray[np.floating[Any]],
        sample_rate: int,
    ) -> AcousticOutput:
        """Run the local model and validate the Member 1 probability contract."""

        self._validate_audio(audio, sample_rate)
        try:
            output = self._runtime.infer(audio, sample_rate)
        except Exception as error:
            raise AcousticInferenceError("model_inference_failed") from error
        try:
            validate_log_probabilities(output.log_probabilities, self._vocabulary)
        except ValueError as error:
            raise AcousticInferenceError("invalid_probability_contract") from error
        if output.vocabulary_version != self._vocabulary.version:
            raise AcousticInferenceError("vocabulary_version_mismatch")
        if output.blank_index != self._vocabulary.blank_index:
            raise AcousticInferenceError("blank_index_mismatch")
        return output

    def score_aligned_attempt(
        self,
        *,
        attempt_id: str,
        acoustic_output: AcousticOutput,
        alignment: AlignmentResult,
        syllables: tuple[SyllableDefinition, ...],
    ) -> AssessmentResult:
        """Produce structured pronunciation evidence after Member 1 alignment."""

        try:
            validate_log_probabilities(acoustic_output.log_probabilities, self._vocabulary)
            phoneme_scores = score_aligned_phonemes(
                acoustic_output,
                alignment,
                self._vocabulary,
                self._config,
            )
            syllable_scores = aggregate_syllables(
                phoneme_scores,
                alignment.phonemes,
                syllables,
                self._config,
            )
        except UnscorableEvidenceError as error:
            return self._neutral_result(attempt_id, acoustic_output, error.reason)
        except ValueError:
            return AssessmentResult(
                attempt_id=attempt_id,
                status="error",
                model_version=acoustic_output.model_version,
                vocabulary_version=acoustic_output.vocabulary_version,
                scoring_version=self._config.scoring_version,
                overall_confidence=0.0,
                reason="invalid_scoring_contract",
            )

        overall_confidence = self._duration_weighted_confidence(
            phoneme_scores,
            alignment,
        )
        statuses = {score.status for score in phoneme_scores}
        assessment_status: AssessmentStatus
        if "unscorable" in statuses:
            assessment_status = "unscorable"
            reason = "phoneme_low_confidence"
        elif "retry" in statuses:
            assessment_status = "retry"
            reason = None
        else:
            assessment_status = "ok"
            reason = None
        return AssessmentResult(
            attempt_id=attempt_id,
            status=assessment_status,
            model_version=acoustic_output.model_version,
            vocabulary_version=acoustic_output.vocabulary_version,
            scoring_version=self._config.scoring_version,
            phoneme_scores=phoneme_scores,
            syllable_scores=syllable_scores,
            overall_confidence=overall_confidence,
            reason=reason,
        )

    @staticmethod
    def _validate_audio(
        audio: npt.NDArray[np.floating[Any]],
        sample_rate: int,
    ) -> None:
        if sample_rate != 16000:
            raise ValueError("acoustic runtime requires a 16000 Hz sample rate")
        if not isinstance(audio, np.ndarray) or audio.ndim != 1:
            raise ValueError("audio must be a mono NumPy array")
        if audio.size == 0:
            raise ValueError("audio must be non-empty")
        if not np.issubdtype(audio.dtype, np.floating):
            raise ValueError("audio must use a floating-point dtype")
        if not np.isfinite(audio).all():
            raise ValueError("audio must contain only finite samples")

    def _neutral_result(
        self,
        attempt_id: str,
        acoustic_output: AcousticOutput,
        reason: str,
    ) -> AssessmentResult:
        return AssessmentResult(
            attempt_id=attempt_id,
            status="unscorable",
            model_version=acoustic_output.model_version,
            vocabulary_version=acoustic_output.vocabulary_version,
            scoring_version=self._config.scoring_version,
            overall_confidence=0.0,
            reason=reason,
        )

    @staticmethod
    def _duration_weighted_confidence(
        scores: tuple[PhonemeScore, ...],
        alignment: AlignmentResult,
    ) -> float:
        weights = tuple(
            phoneme.end_frame - phoneme.start_frame for phoneme in alignment.phonemes
        )
        return sum(
            score.confidence * weight
            for score, weight in zip(scores, weights, strict=True)
        ) / sum(weights)
