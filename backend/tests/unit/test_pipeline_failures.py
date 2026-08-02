from __future__ import annotations

import numpy as np
import pytest

from vaakmitra.contracts.acoustic import AcousticOutput
from vaakmitra.ctc.vocabulary import PhonemeVocabulary
from vaakmitra.pipeline.assessment import AcousticInferenceError, AssessmentPipeline
from vaakmitra.scoring.confidence import ScoringConfig


class FailingRuntime:
    def infer(self, audio: np.ndarray, sample_rate: int) -> AcousticOutput:
        del audio, sample_rate
        raise RuntimeError("secret model path and provider details")


@pytest.fixture
def pipeline() -> AssessmentPipeline:
    vocabulary = PhonemeVocabulary("fixture-vocab-1", ("<blank>", "a", "m"))
    return AssessmentPipeline(
        runtime=FailingRuntime(),
        vocabulary=vocabulary,
        config=ScoringConfig(),
    )


@pytest.mark.parametrize(
    ("audio", "sample_rate", "message"),
    [
        (np.array([], dtype=np.float32), 16000, "non-empty"),
        (np.zeros((2, 2), dtype=np.float32), 16000, "mono"),
        (np.array([0.0, np.nan], dtype=np.float32), 16000, "finite"),
        (np.zeros(10, dtype=np.float32), 8000, "16000"),
    ],
)
def test_pipeline_rejects_invalid_audio_before_runtime(
    pipeline: AssessmentPipeline,
    audio: np.ndarray,
    sample_rate: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        pipeline.infer(audio, sample_rate)


def test_pipeline_maps_runtime_failure_without_leaking_exception(
    pipeline: AssessmentPipeline,
) -> None:
    with pytest.raises(AcousticInferenceError) as raised:
        pipeline.infer(np.zeros(1600, dtype=np.float32), 16000)

    assert str(raised.value) == "model_inference_failed"
    assert "secret" not in str(raised.value)
