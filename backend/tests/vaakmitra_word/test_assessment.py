from __future__ import annotations

from dataclasses import dataclass, replace
import io
import wave

import numpy as np

from app.vaakmitra_word.assessment import AssessmentContext, WordAssessmentService
from app.vaakmitra_word.calibration import CalibrationArtifact, EvidenceCalibrator
from app.vaakmitra_word.classifier import ClassifierArtifact, LinearWordClassifier
from app.vaakmitra_word.contracts import Decision, ModelEvidence, ReasonCode, WordCandidate
from app.vaakmitra_word.dtw import ReferenceBank
from app.vaakmitra_word.model import ModelCapabilityError
from app.vaakmitra_word.policy import SafeAdaptivePolicy, TherapistConstraints


def wav_bytes(amplitude: float = 0.2) -> bytes:
    rate = 16000
    t = np.arange(rate) / rate
    samples = (amplitude * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(samples.tobytes())
    return output.getvalue()


@dataclass
class FakeModel:
    target_probability: float = 0.97
    fail: bool = False
    calls: int = 0
    model_version: str = "synthetic-model"
    model_hash: str = "model-hash"
    ready: bool = True
    is_test_double: bool = True

    def infer(self, samples, sample_rate, target_word):
        self.calls += 1
        if self.fail:
            raise ModelCapabilityError("model_inference_failed")
        return ModelEvidence(
            candidates=[WordCandidate(word=target_word, probability=self.target_probability)],
            target_probability=self.target_probability,
            embeddings=np.array([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32),
            model_version=self.model_version,
            model_hash=self.model_hash,
        )


def service(model: FakeModel) -> WordAssessmentService:
    classifier = LinearWordClassifier(
        ClassifierArtifact(
            version="classifier-1",
            model_hash="model-hash",
            vocabulary_hash="vocab-hash",
            labels=("TA_00021", "OTHER"),
            weights=np.array([[2.0, 0.0], [-2.0, 0.0]]),
            bias=np.zeros(2),
        )
    )
    calibration = CalibrationArtifact(
        version="calibration-1",
        approved=True,
        model_hash="model-hash",
        classifier_hash="classifier-hash",
        reference_bank_hash="reference-hash",
        vocabulary_hash="vocab-hash",
        dataset_manifest_hash="synthetic-dataset",
        feature_order=("p_raw_target", "p_normalized_target", "p_classifier_target", "dtw_similarity"),
        feature_means=(0.0, 0.0, 0.0, 0.0),
        feature_scales=(1.0, 1.0, 1.0, 1.0),
        coefficients=(2.0, 0.5, 2.0, 1.0),
        intercept=-2.5,
        retry_threshold=0.35,
        pass_threshold=0.75,
        max_view_disagreement=0.25,
    )
    return WordAssessmentService(
        model=model,
        classifier=classifier,
        reference_bank=ReferenceBank(
            version="references-1",
            model_hash="model-hash",
            references={"TA_00021": [np.array([[1.0, 0.0]], dtype=np.float32)]},
        ),
        calibrator=EvidenceCalibrator(calibration),
        policy=SafeAdaptivePolicy(),
    )


def context() -> AssessmentContext:
    return AssessmentContext(
        session_id="SES-1",
        attempt_id="ATT-1",
        word_id="TA_00021",
        target_word="அம்மா",
        attempt_count=0,
        therapist_constraints=TherapistConstraints(
            allowed_actions=("repeat", "picture", "next_word", "break", "safe_end"),
            next_exercise_id="TA_00022",
        ),
    )


def test_au009_energy_only_real_model_cannot_pass():
    model = FakeModel()
    model.is_test_double = False
    result = service(model).assess(wav_bytes(), context())
    assert result.decision is Decision.UNSCORABLE
    assert result.word_match_probability is None


def test_au011_unbound_vad_configuration_cannot_enable_scoring():
    from types import SimpleNamespace
    from app.vaakmitra_word.audio import validate_audio
    model = FakeModel()
    model.is_test_double = False
    pipeline = service(model)
    pipeline.vad = SimpleNamespace(ready=True, config_hash='new-vad-hash', validate=validate_audio)
    result = pipeline.assess(wav_bytes(), context())
    assert result.reason_code is ReasonCode.VAD_UNAVAILABLE
    assert result.word_match_probability is None


def test_data013_real_service_rejects_missing_and_mismatched_live_pipeline_binding():
    from types import SimpleNamespace
    from app.vaakmitra_word.audio import validate_audio
    from app.vaakmitra_word.live_evidence import pipeline_fingerprint
    model = FakeModel()
    model.is_test_double = False
    pipeline = service(model)
    pipeline.vad = SimpleNamespace(ready=True, config_hash='vad-hash', validate=validate_audio)
    for live_hash in ('', '0' * 64):
        artifact = pipeline.calibrator.artifact.model_copy(update={
            'vad_config_hash': 'vad-hash', 'live_pipeline_hash': live_hash})
        pipeline.calibrator = EvidenceCalibrator(artifact)
        result = pipeline.assess(wav_bytes(), context())
        assert result.decision is Decision.UNSCORABLE
        assert result.reason_code is ReasonCode.CALIBRATION_UNAVAILABLE
        assert result.word_match_probability is None
    pipeline.calibrator = EvidenceCalibrator(pipeline.calibrator.artifact.model_copy(update={
        'live_pipeline_hash': pipeline_fingerprint(pipeline.normalization)}))
    assert pipeline.assess(wav_bytes(), context()).decision is Decision.PASS


def test_cls004_missing_target_cannot_pass_from_other_families():
    pipeline = service(FakeModel())
    pipeline.classifier = LinearWordClassifier(replace(pipeline.classifier.artifact, labels=('TA_OTHER_WORD', 'OTHER')))
    result = pipeline.assess(wav_bytes(), context())
    assert result.decision is Decision.UNSCORABLE
    assert result.reason_code is ReasonCode.CLASSIFIER_UNAVAILABLE


def test_fake_multi_family_evidence_runs_complete_pass_path() -> None:
    result = service(FakeModel()).assess(wav_bytes(), context())

    assert result.decision is Decision.PASS
    assert result.response_intent == "CELEBRATE"
    assert result.next_exercise_id == "TA_00022"
    assert result.model_version == "synthetic-model"


def test_model_failure_is_unscorable_without_numeric_score() -> None:
    result = service(FakeModel(fail=True)).assess(wav_bytes(), context())

    assert result.decision is Decision.UNSCORABLE
    assert result.reason_code is ReasonCode.MODEL_INFERENCE_FAILED
    assert result.word_match_probability is None


def test_invalid_audio_never_calls_model() -> None:
    model = FakeModel()

    result = service(model).assess(wav_bytes(amplitude=0.0), context())

    assert result.decision is Decision.UNSCORABLE
    assert result.reason_code is ReasonCode.NO_SPEECH
    assert model.calls == 0

