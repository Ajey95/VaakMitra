# DEC-022 local adult website demo

Goal: make the existing loopback Backend Lab demonstrate a real adult Tamil WAV end to end, without presenting child or release readiness.

1. Keep the official DEC-008/015 assessment `UNSCORABLE` and its probability null. Add a separate DEC-022 provisional adult estimate that uses the same live feature transform and calibration coefficients only after artifact, VAD, audio-quality, cross-view, and evidence-family gates pass. Do not persist diagnostic audio/results.
2. Add backend tests for valid adult evidence, invalid/missing/uncertain evidence, hash/runtime mismatch, production endpoint isolation, and response shape. Fail first, implement, rerun.
3. Update the Backend Lab to show the bounded estimate and caveat clearly, with an unavailable state when gates fail. Add browser tests for both states.
4. Verify the actual loopback HTTP app with an adult WAV and the r4 engineering artifact, plus backend/frontend suites. Record exact evidence and remaining child/mobile/release gates, without claiming them complete.
