"""AU-007..011: local Silero ONNX inference with capture-local recurrent state.

Tensor contract: snakers4/silero-vad utils_vad.py at
867c2aa692646a1f1de3e94a15c9dd9f614c0acb (MIT).
"""
from pathlib import Path
from typing import Literal
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from .audio import validate_audio
from .model import ModelCapabilityError, sha256_file


class VadConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    schema_version: Literal['vaakmitra-vad-1']
    model_path: str
    model_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    threshold: float = Field(default=0.5, gt=0, lt=1)
    min_speech_ms: int = Field(default=200, ge=200, le=500)
    pause_tolerance_ms: int = Field(default=700, ge=300, le=1200)


def merge_regions(regions, tolerance):
    merged = []
    for start, end in regions:
        if merged and start - merged[-1][1] <= tolerance:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


class OnnxVad:
    @classmethod
    def from_config(cls, config_path):
        path = Path(config_path)
        config = VadConfig.model_validate_json(path.read_text(encoding='utf-8'))
        model = Path(config.model_path)
        if not model.is_absolute():
            model = (path.parent / model).resolve()
            if not model.is_relative_to(path.parent.resolve()):
                raise ModelCapabilityError('vad_path_outside_bundle')
        if not model.is_file() or sha256_file(model) != config.model_sha256:
            raise ModelCapabilityError('vad_integrity_mismatch')
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.inter_op_num_threads = options.intra_op_num_threads = 1
        session = ort.InferenceSession(str(model), providers=['CPUExecutionProvider'], sess_options=options)
        return cls(config, sha256_file(path), session)

    def __init__(self, config, config_hash, session):
        self.config, self.config_hash, self.session = config, config_hash, session
        self.ready = session is not None

    def validate(self, samples, sample_rate):
        quality = validate_audio(samples, sample_rate)
        if sample_rate != 16000:
            raise ModelCapabilityError('vad_input_invalid')
        # Retain physical capture checks. Energy never supplies the speech verdict.
        if quality.reason not in (None, 'no_speech'):
            return quality.model_copy(update={'vad_mode': 'onnx_cpu'})
        state = np.zeros((2, 1, 128), dtype=np.float32)
        context = np.zeros((1, 64), dtype=np.float32)
        regions = []
        active_samples = 0
        try:
            for offset in range(0, len(samples), 512):
                chunk = np.asarray(samples[offset:offset + 512], dtype=np.float32)
                length = len(chunk)
                chunk = np.pad(chunk, (0, 512 - length))[None, :]
                values = np.concatenate((context, chunk), axis=1)
                probability, state = self.session.run(None, {'input': values, 'state': state,
                                                             'sr': np.array(16000, dtype=np.int64)})
                probability = float(np.asarray(probability).reshape(-1)[0])
                if not np.isfinite(probability) or not 0 <= probability <= 1 or not np.isfinite(state).all():
                    raise ValueError('invalid VAD outputs')
                context = values[:, -64:]
                if probability >= self.config.threshold:
                    regions.append((offset, offset + length))
                    active_samples += length
        except Exception as exc:
            raise ModelCapabilityError('vad_inference_failed') from exc
        speech_duration_s = active_samples / 16000
        speech = speech_duration_s >= max(0.20, self.config.min_speech_ms / 1000)
        reason = ('no_speech' if not speech else 'speech_too_long' if speech_duration_s > 8.0
                  else 'excessive_noise_or_low_level' if not quality.snr_acceptable else None)
        merged = merge_regions(regions, self.config.pause_tolerance_ms * 16)
        return quality.model_copy(update={'valid': reason is None, 'reason': reason,
            'speech_detected': speech, 'speech_duration_s': speech_duration_s,
            'speech_regions': [(start / 16000, end / 16000) for start, end in merged], 'vad_mode': 'onnx_cpu'})
