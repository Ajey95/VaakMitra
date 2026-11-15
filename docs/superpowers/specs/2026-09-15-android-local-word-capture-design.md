# Android Local Word Capture Design

Authority: `VAAKMITRA_FINAL_SSOT.md` v3.3.1, especially DEC-003/013, AU-001..006, FUS-007, MOD-006, PRV-001/002, and UX-003/007. This is the first independently testable Android slice toward the private on-device build. It does not change product requirements or artifact approval.

## Problem and boundary

The inherited `SpeakEasyAndroid` word screen writes AAC to cache, sends it to the retired `/api/evaluate/speech` route, substitutes zero for missing accuracy, and may save fabricated stars/progress. There is no Android student bundle to replace that service yet. Android word practice must remain usable without a network or scorer, but must never claim a correctness result from absent model evidence.

## Design

For word practice, capture mono 16-kHz PCM16 with Android `AudioRecord` in a bounded in-memory buffer. Limit capture to eight seconds, stop and release the microphone before any result is shown, and clear raw samples after local evaluation. Audio is never written to a file, logged, or sent to an API. The existing candle game keeps its amplitude-only recorder unchanged.

A small `LocalWordPractice` boundary accepts the target word and captured PCM, checks duration and clipping, and returns only `UNSCORABLE` with a reason while the student bundle is absent. The interface will later host the local VAD/student/classifier/calibration pipeline; there is no server fallback. Invalid/short/no-sample capture returns a local retry instruction. The word screen gives a Tamil target prompt, allows a new whole-word attempt or exit, shows no percentage, transcription, syllable score, star award, or progress mutation. The microphone cannot listen during prompt playback. Child-facing copy remains supportive and does not diagnose a sound.

The Android `AppViewModel` no longer owns a word-evaluation upload method; the Retrofit legacy evaluation and score-saving methods are removed from this word flow. Auth/profile/catalog networking elsewhere is not changed in this slice. The next independently testable slice will package an actual INT8 student and replace the fail-closed local evaluator, followed by offline catalog/session/report integration and physical-device tests.

## Acceptance

- Pure Kotlin tests cover capture duration/size, invalid/silent/clipped capture, and missing-model abstention with null score.
- Android debug build and unit tests pass; source contains no word-practice call to `/api/evaluate/speech` or audio multipart upload.
- Cancel, screen exit, and stop release capture; a capture has at most 128,000 samples and no file artifact.
- This slice is described as local practice without scoring, not as completed Android edge recognition or clinical accuracy.
