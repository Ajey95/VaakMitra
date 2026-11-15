"""DEC-018/PRV-002: local capability isolation and truthful diagnostic evidence."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.config import settings
from app.vaakmitra_word import diagnostics
from app.vaakmitra_word.contracts import AssessmentResult, ReasonCode, WordCandidate
from app.vaakmitra_word.calibration import EvidenceCalibrator
from app.vaakmitra_word.contracts import AssessmentEvidence, AudioQuality, EvidenceItem
from test_calibration import artifact
from test_api import pcm_wav


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(settings, 'APP_ENV', 'development')
    monkeypatch.setattr(settings, 'VAAKMITRA_DIAGNOSTICS_ENABLED', True)
    monkeypatch.setattr(settings, 'CORS_ORIGINS', 'http://127.0.0.1:5173')
    monkeypatch.setattr(diagnostics, '_capabilities', {})
    app = FastAPI()
    app.include_router(diagnostics.router)
    return TestClient(app, client=('127.0.0.1', 50100), headers={'Origin': 'http://127.0.0.1:5173'})


def test_dec018_requires_local_capability_and_revokes_on_close(api):
    assert api.get('/api/dev/word-lab/status').status_code == 401
    assert api.post('/api/dev/word-lab/open', json={'adult_test_only': False}).status_code == 422
    response = api.post('/api/dev/word-lab/open', json={'adult_test_only': True})
    assert response.status_code == 200
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=strict' in response.headers['set-cookie']
    assert api.get('/api/dev/word-lab/status').status_code == 200
    assert api.post('/api/dev/word-lab/close').status_code == 200
    assert api.get('/api/dev/word-lab/status').status_code == 401


def test_dec018_foreign_origin_and_production_denied(api, monkeypatch):
    assert api.post('/api/dev/word-lab/open', json={'adult_test_only': True},
                    headers={'Origin': 'https://untrusted.example'}).status_code == 403
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    assert api.post('/api/dev/word-lab/open', json={'adult_test_only': True}).status_code == 404


def test_dec018_real_route_keeps_engineering_unscorable_and_ephemeral(api, monkeypatch):
    class Service:
        def assess(self, data, context):
            assert data == pcm_wav()
            assert context.session_id.startswith('DIAG-')
            return AssessmentResult.unscorable(ReasonCode.CALIBRATION_UNAVAILABLE,
                session_id=context.session_id, attempt_id=context.attempt_id,
                word_id=context.word_id, target_word=context.target_word)
    monkeypatch.setattr(diagnostics.diagnostic_runtime, 'service', Service())
    monkeypatch.setattr(diagnostics.diagnostic_runtime, 'words', {'W1': 'அம்மா'})
    assert api.post('/api/dev/word-lab/open', json={'adult_test_only': True}).status_code == 200
    response = api.post('/api/dev/word-lab/assess', data={'word_id': 'W1'},
                        files={'audio': ('adult.wav', pcm_wav(), 'audio/wav')})
    assert response.status_code == 200
    body = response.json()
    assert body['persisted'] is False and body['scoring_ready'] is False
    assert body['result']['word_match_probability'] is None
    assert body['result']['decision'] == 'UNSCORABLE'
    assert body['adult_preview']['status'] == 'unavailable'
    assert body['development_result']['decision'] == 'DEV_UNAVAILABLE'
    assert body['development_result']['estimate'] is None
    assert body['chunk_coach']['status'] == 'visual_only'
    assert api.post('/api/dev/word-lab/assess', data={'word_id': 'W1'},
                    files={'audio': ('empty.wav', b'', 'audio/wav')}).status_code == 400


def test_dch002_adult_route_adds_only_transient_text_focus(api, monkeypatch):
    class Service:
        def assess(self, _data, context):
            return AssessmentResult.unscorable(ReasonCode.CALIBRATION_UNAVAILABLE,
                session_id=context.session_id, attempt_id=context.attempt_id,
                word_id=context.word_id, target_word=context.target_word,
                quality=AudioQuality(valid=True, vad_mode='onnx_cpu', speech_detected=True,
                                     snr_acceptable=True, speech_duration_s=.8)).model_copy(update={
                'observed_candidates': [WordCandidate(word='அம்மி', probability=.8)]})
    monkeypatch.setattr(diagnostics.diagnostic_runtime, 'service', Service())
    monkeypatch.setattr(diagnostics.diagnostic_runtime, 'words', {'W1': 'அம்மா'})
    assert api.post('/api/dev/word-lab/open', json={'adult_test_only': True}).status_code == 200
    response = api.post('/api/dev/word-lab/assess', data={'word_id': 'W1'},
                        files={'audio': ('adult.wav', pcm_wav(), 'audio/wav')})
    assert response.status_code == 200
    body = response.json()
    assert body['result']['decision'] == 'UNSCORABLE'
    assert body['result']['word_match_probability'] is None
    assert body['persisted'] is False
    assert body['chunk_coach']['chunks'] == ['அம்', 'மா']
    assert body['chunk_coach']['focus_position'] == 'end'
    assert body['chunk_coach']['basis'] == 'unvalidated_asr_text_difference'
    assert 'candidate' not in body['chunk_coach']


def test_dec022_preview_requires_bound_live_pipeline_and_vad():
    class Service:
        calibrator = EvidenceCalibrator(artifact(approved=False).model_copy(update={
            'population': 'adult_only_engineering', 'live_pipeline_hash': 'fingerprint', 'vad_config_hash': 'vad'}))
        live_pipeline_ready = True
        production_vad_ready = True

    evidence = AssessmentEvidence(original_asr=EvidenceItem(available=True, target_probability=.97),
        normalized_asr=EvidenceItem(available=True, target_probability=.95),
        word_classifier=EvidenceItem(available=True, target_probability=.96),
        embedding_dtw=EvidenceItem(available=True, similarity=.90))
    quality = AudioQuality(valid=True, vad_mode='onnx_cpu', speech_detected=True,
        snr_acceptable=True, speech_duration_s=.8)
    result = AssessmentResult.unscorable(ReasonCode.CALIBRATION_UNAVAILABLE,
        session_id='DIAG-1', attempt_id='ATT-1', word_id='W1', target_word='அம்மா',
        evidence=evidence, quality=quality)
    preview = diagnostics.adult_preview_for_result(Service(), result)
    assert preview['status'] == 'provisional' and preview['estimate'] > .75
    assert result.word_match_probability is None
    Service.live_pipeline_ready = False
    assert diagnostics.adult_preview_for_result(Service(), result)['estimate'] is None
    Service.live_pipeline_ready = True
    Service.production_vad_ready = False
    assert diagnostics.adult_preview_for_result(Service(), result)['estimate'] is None
