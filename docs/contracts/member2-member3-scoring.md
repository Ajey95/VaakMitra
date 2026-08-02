# Member 2 to Member 3 Scoring Contract

`AssessmentPipeline.score_aligned_attempt` returns an `AssessmentResult` with no raw audio or
voice-derived arrays:

```json
{
  "attempt_id": "ATT-00031",
  "status": "ok",
  "model_version": "ta-phoneme-ctc-1.0.0",
  "vocabulary_version": "ta-phonemes-1.0.0",
  "scoring_version": "gop-baseline-1.0.0",
  "phoneme_scores": [
    {
      "phoneme": "a",
      "gop": 0.9,
      "confidence": 0.92,
      "status": "pass",
      "start_ms": 40.0,
      "end_ms": 160.0,
      "reason": null
    }
  ],
  "syllable_scores": [
    {
      "syllable": "அம்",
      "score": 0.86,
      "confidence": 0.88,
      "status": "pass",
      "phoneme_indices": [0]
    }
  ],
  "overall_confidence": 0.84,
  "reason": null
}
```

Assessment statuses are:

- `ok`: evidence is usable; individual units may still be `coach`;
- `retry`: at least one confident unit is below the coaching threshold;
- `unscorable`: evidence is insufficient and must receive a neutral response;
- `error`: an input contract is inconsistent.

Member 3 may convert evidence to therapist-approved actions, but must not change the GOP value or
present `unscorable` as incorrect pronunciation. Every persisted score record must retain all three
versions. Probability arrays, embeddings, audio, and free-speech transcripts are forbidden from the
Member 3 input and sync payload.

