"""DEC-015/DATA-008: offline evidence must use the live feature implementation."""
import hashlib

import pytest

from app.vaakmitra_word.calibration import EvidenceCalibrator
from app.vaakmitra_word.contracts import AssessmentEvidence, AudioQuality, EvidenceItem
from test_assessment import FakeModel, service, context, wav_bytes


def test_live_features_preserve_missing_masks_and_actual_quality():
    evidence = AssessmentEvidence(
        original_asr=EvidenceItem(available=True, target_probability=0.75, top1_is_target=True),
        normalized_asr=EvidenceItem(available=False),
        word_classifier=EvidenceItem(available=True, target_probability=0.2),
        embedding_dtw=EvidenceItem(available=True, similarity=0.4), classifier_entropy=0.3)
    values = EvidenceCalibrator.features(evidence, AudioQuality(
        valid=True, speech_detected=True, speech_duration_s=0.4, snr_acceptable=False))
    assert values['duration_quality'] == 0.5
    assert values['noise_quality'] == 0.0
    assert values['dtw_similarity'] == 0.4
    assert values['p_normalized_target'] is None
    assert values['missing__p_normalized_target'] == 1.0


def test_live_extract_uses_real_service_result_without_approval():
    from app.vaakmitra_word.live_evidence import extract_attempt
    engine = service(FakeModel())
    engine.reference_bank.references['TA_00021'] *= 3  # Three explicit synthetic references.
    engine.calibrator = EvidenceCalibrator(engine.calibrator.artifact.model_copy(update={'approved': False}))
    audio = wav_bytes()
    result = extract_attempt(engine, audio, context(), expected_sha256=hashlib.sha256(audio).hexdigest())
    assert result['features']['dtw_similarity'] == 1.0
    assert result['features']['duration_quality'] == 1.0
    assert result['live_decision'] == 'UNSCORABLE'
    assert engine.calibrator.artifact.approved is False


def test_changed_audio_is_rejected_before_inference():
    from app.vaakmitra_word.live_evidence import extract_attempt
    model = FakeModel()
    with pytest.raises(ValueError, match='audio_integrity_mismatch'):
        extract_attempt(service(model), wav_bytes(), context(), expected_sha256='0' * 64)
    assert model.calls == 0


def test_build_cli_constructs_complete_live_context():
    import runpy
    from pathlib import Path
    module = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts/model/rebuild_live_evidence.py'))
    ctx = module['build_context']('attempt1', 'TA_WORD_0001', 'அம்மா')
    assert ctx.therapist_constraints.next_exercise_id == 'TA_WORD_0001'
    assert ctx.target_word == 'அம்மா'


def test_adult_partition_never_reuses_classifier_train_or_final_evaluation():
    from app.vaakmitra_word.live_evidence import partition_calibration_speakers
    records = [{'speaker_pseudonym': f's{i}', 'split': 'calibration'} for i in range(12)]
    records += [{'speaker_pseudonym': 'TRAIN', 'split': 'train'},
                {'speaker_pseudonym': 'FINAL', 'split': 'evaluation'}]
    parts = partition_calibration_speakers(records)
    assert set(parts) == {f's{i}' for i in range(12)}
    assert set(parts.values()) == {'train', 'calibration', 'evaluation'}
    assert parts == partition_calibration_speakers(list(reversed(records)))
    with pytest.raises(ValueError, match='speaker_split_leakage'):
        partition_calibration_speakers(records + [{'speaker_pseudonym': 's0', 'split': 'train'}])


def test_data013_pipeline_fingerprint_changes_with_effective_normalization_config():
    from app.vaakmitra_word.live_evidence import pipeline_fingerprint
    from app.vaakmitra_word.normalization import NormalizationConfig
    assert pipeline_fingerprint(NormalizationConfig(peak_target=0.80)) != pipeline_fingerprint()
