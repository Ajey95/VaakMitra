from __future__ import annotations

import numpy as np

from vaakmitra.contracts.acoustic import AcousticOutput
from vaakmitra.contracts.alignment import AlignedPhoneme, AlignmentResult, SyllableDefinition
from vaakmitra.ctc.vocabulary import PhonemeVocabulary
from vaakmitra.pipeline.assessment import AssessmentPipeline
from vaakmitra.scoring.confidence import ScoringConfig


class FixtureRuntime:
    def __init__(self, vocabulary: PhonemeVocabulary) -> None:
        self.vocabulary = vocabulary

    def infer(self, audio: np.ndarray, sample_rate: int) -> AcousticOutput:
        del audio, sample_rate
        probabilities = np.log(
            np.array(
                [
                    [0.05, 0.90, 0.05],
                    [0.05, 0.85, 0.10],
                    [0.05, 0.10, 0.85],
                    [0.05, 0.05, 0.90],
                ],
                dtype=np.float32,
            )
        )
        return AcousticOutput(
            log_probabilities=probabilities,
            frame_shift_ms=20.0,
            model_version="fixture-model-1.0.0",
            vocabulary_version=self.vocabulary.version,
            blank_index=self.vocabulary.blank_index,
            vocabulary_size=len(self.vocabulary.tokens),
        )


def _alignment(confidence: float = 0.9) -> AlignmentResult:
    return AlignmentResult(
        status="valid",
        confidence=confidence,
        phonemes=(
            AlignedPhoneme(
                phoneme="a",
                start_frame=0,
                end_frame=2,
                start_ms=0.0,
                end_ms=40.0,
                confidence=0.9,
            ),
            AlignedPhoneme(
                phoneme="m",
                start_frame=2,
                end_frame=4,
                start_ms=40.0,
                end_ms=80.0,
                confidence=0.9,
            ),
        ),
    )


def test_pipeline_exposes_probabilities_then_scores_member1_alignment() -> None:
    vocabulary = PhonemeVocabulary(
        version="fixture-vocab-1.0.0",
        tokens=("<blank>", "a", "m"),
    )
    pipeline = AssessmentPipeline(
        runtime=FixtureRuntime(vocabulary),
        vocabulary=vocabulary,
        config=ScoringConfig(scoring_version="fixture-gop-1.0.0"),
    )

    acoustic_output = pipeline.infer(
        audio=np.zeros(3200, dtype=np.float32),
        sample_rate=16000,
    )
    result = pipeline.score_aligned_attempt(
        attempt_id="ATT-1",
        acoustic_output=acoustic_output,
        alignment=_alignment(),
        syllables=(SyllableDefinition(text="அம்", phoneme_indices=(0, 1)),),
    )

    assert acoustic_output.log_probabilities.shape == (4, 3)
    assert result.status == "ok"
    assert result.model_version == "fixture-model-1.0.0"
    assert result.vocabulary_version == "fixture-vocab-1.0.0"
    assert result.scoring_version == "fixture-gop-1.0.0"
    assert tuple(score.phoneme for score in result.phoneme_scores) == ("a", "m")
    assert result.syllable_scores[0].syllable == "அம்"
    assert result.reason is None


def test_pipeline_returns_neutral_result_for_low_alignment_confidence() -> None:
    vocabulary = PhonemeVocabulary("fixture-vocab-1.0.0", ("<blank>", "a", "m"))
    pipeline = AssessmentPipeline(
        runtime=FixtureRuntime(vocabulary),
        vocabulary=vocabulary,
        config=ScoringConfig(),
    )
    output = pipeline.infer(np.zeros(1600, dtype=np.float32), 16000)

    result = pipeline.score_aligned_attempt(
        attempt_id="ATT-2",
        acoustic_output=output,
        alignment=_alignment(confidence=0.2),
        syllables=(SyllableDefinition(text="அம்", phoneme_indices=(0, 1)),),
    )

    assert result.status == "unscorable"
    assert result.reason == "alignment_low_confidence"
    assert result.phoneme_scores == ()
    assert result.syllable_scores == ()

