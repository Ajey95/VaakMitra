"""DATA-001/004/008: adult build evidence from the exact product service path."""
from hashlib import sha256
from dataclasses import asdict
import json
from pathlib import Path

from .calibration import BASE_FEATURES, EvidenceCalibrator
from .normalization import NormalizationConfig


def pipeline_fingerprint(normalization: NormalizationConfig | None = None) -> str:
    """Fingerprint executable preprocessing/inference/features, independent of CRLF."""
    root = Path(__file__).parent
    digest = sha256()
    for name in ('audio.py', 'normalization.py', 'model.py', 'classifier.py', 'dtw.py',
                 'vad.py', 'assessment.py', 'calibration.py', 'live_evidence.py'):
        digest.update(name.encode('ascii'))
        digest.update((root / name).read_bytes().replace(b'\r\n', b'\n'))
    digest.update(json.dumps(asdict(normalization or NormalizationConfig()),
                             sort_keys=True, separators=(',', ':')).encode('utf-8'))
    return digest.hexdigest()


def partition_calibration_speakers(records: list[dict], *, source_split='calibration') -> dict[str, str]:
    """Reserve original evaluation and classifier/reference train speakers entirely.

    Split only the old adult calibration partition into fusion fit, operating-point
    selection and engineering evaluation. This is not a child validation split.
    """
    seen = {}
    for row in records:
        speaker, split = row['speaker_pseudonym'], row['split']
        if seen.setdefault(speaker, split) != split:
            raise ValueError('speaker_split_leakage')
    speakers = sorted((s for s, split in seen.items() if split == source_split),
                      key=lambda s: sha256(s.encode()).hexdigest())
    if len(speakers) < 6:
        raise ValueError('insufficient_independent_calibration_speakers')
    fit_end, tune_end = max(2, len(speakers) // 2), max(4, len(speakers) * 3 // 4)
    return {s: ('train' if i < fit_end else 'calibration' if i < tune_end else 'evaluation')
            for i, s in enumerate(speakers)}


def extract_attempt(service, audio: bytes, context, *, expected_sha256: str) -> dict:
    if sha256(audio).hexdigest() != expected_sha256:
        raise ValueError('audio_integrity_mismatch')
    result = service.assess(audio, context)
    values = EvidenceCalibrator.features(result.evidence, result.quality)
    return {'features': {name: values[name] for name in sorted(BASE_FEATURES)},
            'live_decision': result.decision.value, 'reason_code': result.reason_code.value,
            'quality_valid': result.quality.valid, 'vad_mode': result.quality.vad_mode,
            'evidence_available': bool(result.evidence.original_asr.available
                and result.evidence.word_classifier.available and result.evidence.embedding_dtw.available),
            'latency_ms': result.latency_ms}
