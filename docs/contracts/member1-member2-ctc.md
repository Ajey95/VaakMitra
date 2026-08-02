# Member 1 to Member 2 CTC and Alignment Contract

## Member 1 supplies audio

Member 1 supplies an in-memory NumPy waveform meeting all of these conditions:

- mono, one-dimensional floating-point samples;
- exactly 16,000 Hz;
- non-empty and finite;
- already validated for VAD, capture quality, duration, and prompt leakage.

Member 2 does not resample, persist, upload, or quality-judge this audio.

## Member 2 returns acoustic probabilities

`AssessmentPipeline.infer(audio, 16000)` returns `AcousticOutput`:

```json
{
  "log_probabilities": "float32[frames,vocabulary_size] in memory only",
  "frame_shift_ms": 20.0,
  "model_version": "ta-phoneme-ctc-1.0.0",
  "vocabulary_version": "ta-phonemes-1.0.0",
  "blank_index": 0,
  "vocabulary_size": 42
}
```

Each frame must normalize to one in probability space. Member 1 must use the declared frame shift,
blank index, and exact ordered vocabulary version. The matrix must not be logged, persisted, or
synchronized.

## Member 1 returns alignment

Each `AlignedPhoneme` uses half-open frame bounds `[start_frame, end_frame)` and includes matching
millisecond bounds plus confidence in `[0,1]`. A valid `AlignmentResult` contains at least one
phoneme. An invalid result contains a neutral failure reason.

Member 2 rejects scoring for invalid alignment, low global confidence, unknown phonemes, empty
segments, out-of-range frames, or version/blank mismatches. The neutral reasons are:

- `alignment_invalid`;
- `alignment_low_confidence`;
- `phoneme_not_in_vocabulary`;
- `segment_out_of_bounds`;
- `empty_aligned_segment`;
- `vocabulary_version_mismatch`;
- `vocabulary_size_mismatch`;
- `blank_index_mismatch`.

