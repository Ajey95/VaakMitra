"""AU-007..011: pause merging and per-capture ONNX execution, no energy fallback."""
import json
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from app.vaakmitra_word.vad import OnnxVad, VadConfig, merge_regions
from app.vaakmitra_word.model import ModelCapabilityError, sha256_file


def test_au007_merge_keeps_within_word_pause_but_not_long_gap():
    assert merge_regions([(0, 200), (800, 1000), (2300, 2500)], 700) == [(0, 1000), (2300, 2500)]


def configured(tmp_path, monkeypatch, *, fail=False):
    model = tmp_path / 'vad.onnx'
    model.write_bytes(b'onnx-test-double')
    path = tmp_path / 'vad.json'
    path.write_text(json.dumps({'schema_version': 'vaakmitra-vad-1', 'model_path': str(model),
        'model_sha256': sha256_file(model)}))
    calls = []
    class Session:
        def __init__(self, *args, **kwargs):
            assert kwargs['providers'] == ['CPUExecutionProvider']
        def run(self, outputs, inputs):
            if fail:
                raise RuntimeError('broken model')
            calls.append(inputs['state'].copy())
            assert inputs['input'].shape == (1, 576)
            return np.array([[0.9]], dtype=np.float32), inputs['state'] + 1
    monkeypatch.setitem(sys.modules, 'onnxruntime', SimpleNamespace(SessionOptions=SimpleNamespace, InferenceSession=Session))
    return OnnxVad.from_config(path), calls


def test_au008_executes_every_chunk_and_resets_state_between_captures(tmp_path, monkeypatch):
    vad, calls = configured(tmp_path, monkeypatch)
    audio = np.full(16000, 0.02, dtype=np.float32)
    first = vad.validate(audio, 16000)
    second = vad.validate(audio, 16000)
    assert first.valid and second.valid
    assert first.vad_mode == 'onnx_cpu' and first.speech_detected
    assert len(calls) == 64
    assert np.count_nonzero(calls[0]) == np.count_nonzero(calls[32]) == 0
    assert np.count_nonzero(calls[1]) > 0


def test_au009_runtime_failure_never_falls_back_to_energy(tmp_path, monkeypatch):
    vad, _ = configured(tmp_path, monkeypatch, fail=True)
    with pytest.raises(ModelCapabilityError):
        vad.validate(np.full(16000, 0.02, dtype=np.float32), 16000)


def test_au003_detected_speech_exactly_eight_seconds_is_valid(tmp_path, monkeypatch):
    vad, _ = configured(tmp_path, monkeypatch)
    quality = vad.validate(np.full(8 * 16000, 0.02, dtype=np.float32), 16000)
    assert quality.valid is True
    assert quality.speech_duration_s == 8.0


def test_au003_detected_speech_over_eight_seconds_is_invalid(tmp_path, monkeypatch):
    vad, _ = configured(tmp_path, monkeypatch)
    quality = vad.validate(np.full(10 * 16000, 0.02, dtype=np.float32), 16000)
    assert quality.valid is False
    assert quality.reason == 'speech_too_long'
    assert quality.speech_duration_s == 10.0


def test_au003_long_capture_with_short_separated_voiced_regions_is_valid(tmp_path, monkeypatch):
    vad, _ = configured(tmp_path, monkeypatch)
    class SparseSession:
        def run(self, _outputs, inputs):
            chunk = inputs['input'][0, 64:]
            return np.array([[0.9 if np.max(np.abs(chunk)) > 0.01 else 0.1]], dtype=np.float32), inputs['state']
    vad.session = SparseSession()
    audio = np.zeros(10 * 16000, dtype=np.float32)
    audio[:16000] = 0.02
    audio[-16000:] = 0.02
    quality = vad.validate(audio, 16000)
    assert quality.valid is True
    assert 1.9 <= quality.speech_duration_s <= 2.1
    assert quality.duration_s == 10.0


def test_au003_vad_config_cannot_lower_product_speech_minimum_to_100ms():
    with pytest.raises(ValueError):
        VadConfig(schema_version='vaakmitra-vad-1', model_path='synthetic',
            model_sha256='a' * 64, min_speech_ms=100)
