# Focused word/model implementation plan

> Execute inline using superpowers:executing-plans; TDD for meaningful data/safety logic; one fresh final review.

Goal: expand app to25words with18focus and perform bounded localGPU continuation. Spec: docs/superpowers/specs/2026-11-12-focused-words-design.md. Existing isolated dirty lab branch remains; no commits/cleanup. DEC058/PHN001..006, privacy/scoring/avatar requirements remain binding.

## Review Focus
- Appended IDs/numeric routes and closed prompts agree, original19stable, no classifier fallback for missing new targets.
- Complete original audio, split/parent/hash/speaker guards and cache bindings, including audit separation.
- No expected word in decoder; strict same-row metrics and immutable caps; failed candidates never overwriteV7.
- Calibration-only checkpoint choice and independently timestamped freeze before test; no test-based reselection.
- Public fixtures/synthetic provenance and adult-only evidence, RAM-only mic, preserved app theme/session/avatars.

## Task1 data/training contract
- [x] Tests for stable packIDs, training-only balanced sampler, sidecar indices, split leakage/no crop, explicit aggregate counts/strict promotion and freeze bindings; watch RED before implementation.
- [x] Implement dedicated focused_phoneme_update.py reusing existing model/decoder/augmentation primitives, immutable manifests and mmap+sidecar cache; Python targeted/full phoneme tests green.
- [x] Snapshot scripts/config and input hashes; run two declared CUDA controls, logs/VRAM/checkpoints, calibration choice only. Freeze or record no eligible candidate. Budget disk <400MiB additional and stop below250MiB free.

## Task2 vocabulary/app and conditional model
- [x] JVM/catalogue tests RED; append6 stable items, focused18/all25 filtering, dynamiccounts, registry v1.1 with4intended pending IDs. Existing nineteen and session callbacks preserved.
- [x] If eligible freeze single candidate, export FP32 unchanged contract and compare same-row exposed test/newword/old19/broader caps, public adult stress and desktop/native parity; reject toV7 on failure. No test reselection.
- [x] Bind installed metadata to25 IDs; no new token invention/score approval. Keep previous model/APK/source rollback.

## Task3 validation/review/delivery
- [x] Scoped Python/JVM/lint/build bothABI/test, native parity and newIDs waveform-only preview, focused/all navigation; inspect rendered list at normal/2x without real audio.
- [x] ONE fresh most-capable read-only whole-scope reviewer, regrade and ONE Important RED/GREEN fix pass, defer minors, no rereview.
- [x] Verify app/test/model/catalogue hashes, archive APK/source/results/metrics/actualGPU runtime, update currentcontext, keep branch/evidence as-is. Phone as available; no private capture or claimed child quality.
