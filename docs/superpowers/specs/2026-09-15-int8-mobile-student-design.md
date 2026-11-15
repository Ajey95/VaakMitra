# VaakMitra INT8 Mobile Student Design

**Status:** Approved for implementation on 2026-09-15  
**Normative source:** `VAAKMITRA_FINAL_SSOT.md` version 3.3.7  
**Applicable IDs:** DEC-003/004/007/008/013/014/015/016/017/028, AU-002..011, MOD-001..008, MST-001..010, CLS-001..005, FUS-001..007, DATA-001..013, UX-003/006/010, GATE-01..06

## Outcome and boundary

Build `vm-mobile-student-ta19-v0`, a fully offline Android engineering scorer for the existing 19-word starter path. It must replace `MODEL_UNAVAILABLE` only when the exact hash-bound bundle loads. Its visible outcome is an adult-engineering `DEV_*` interaction result; the official child/product result remains `UNSCORABLE`, `word_match_probability` remains null, and release builds keep the scorer disabled.

This bundle is not the 100-word V1 release model and does not establish child, clinical, physical-device, or production readiness.

## Frozen inputs

- Teacher model: `D:\VaakMitraModels\ta-word-v1\upstream\indicconformer_stt_ta_hybrid_rnnt_large.nemo`, expected SHA-256 `40a6fce3374ceb67daa2a071e92f0948c51c6a95b734d4881a3bcfe0b1bed32a`.
- Teacher engineering classifier: `D:\VaakMitraData\artifacts\engineering\word-classifier.npz`.
- Reviewed adult/public manifest: `D:\VaakMitraData\manifests\openslr127-word-v1-reviewed.jsonl`.
- Audio root: `D:\VaakMitraData\prepared\openslr127-word-v1`.
- Teacher embedding shards: `D:\VaakMitraData\embeddings\openslr127-word-v1-engineering`.
- VAD model: `/home/vab/.local/share/vaakmitra/backend-lab/downloads/silero_vad.onnx`, expected SHA-256 `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`.
- Target data: 1,197 clips across the 19 canonical Android words; train/calibration/evaluation counts are 985/105/107.
- `OTHER` data: 14,033 clips; train/calibration/evaluation counts are 11,112/1,447/1,474.
- The repository `eval/` child material is excluded from training, calibration, threshold selection, and this adult evaluation.

The build script must verify these counts and hashes from the inputs instead of trusting this prose.

## Vocabulary

The ordered output labels are the Android `StarterWords` IDs `TA_WORD_0001`, `TA_WORD_0002`, `TA_WORD_0012`, `TA_WORD_0013`, `TA_WORD_0014`, `TA_WORD_0015`, `TA_WORD_0016`, `TA_WORD_0017`, `TA_WORD_0049`, `TA_WORD_0050`, `TA_WORD_0072`, `TA_WORD_0082`, `TA_WORD_0083`, `TA_WORD_0086`, `TA_WORD_0090`, `TA_WORD_0096`, `TA_WORD_0098`, `TA_WORD_0099`, `TA_WORD_0100`, followed by `OTHER`. `labels.json` also binds Tamil display text and English transliteration. Android targets by ID, never by array position or user-supplied Tamil text.

## Signal contract

Android records PCM16 mono at 16 kHz and performs the existing bounded capture checks. The model input is float32 `[1, 32000]`: signed PCM16 divided by 32768, longer arrays centre-cropped, shorter arrays symmetrically zero-padded. The exact same Python and Kotlin preprocessing algorithms are checked against a committed golden vector. Raw PCM is held only in memory and zeroed after inference or cancellation.

Silero VAD executes locally before scoring. Its state is reset for each capture. The shipped configuration binds 16 kHz, threshold 0.5, minimum speech 200 ms, merge tolerance 700 ms, and the model SHA-256. If VAD cannot load or detects no valid speech, the engineering result is unavailable; energy checks may reject a capture but cannot authorize a match.

## Student network and training

The model is a compact one-dimensional depthwise-separable convolutional network. A strided 25 ms stem converts the two-second waveform to frames; four residual depthwise-separable blocks expand channels to 96 and downsample time. Mask-free global average pooling feeds a 64-dimensional L2-normalized embedding and a linear 20-class head. ONNX outputs are named `embedding` and `logits`.

Training is deterministic for a recorded seed. It uses speaker-disjoint manifest partitions, balanced target/`OTHER` sampling, gain/noise/time-shift augmentation on the training split only, and no child samples. Loss is `0.6 * cross_entropy(hard_label) + 0.4 * KL(student/T, teacher/T) * T^2` with `T=2`. Teacher soft labels are computed from the frozen teacher embedding shards and classifier; every sample without valid teacher evidence is logged and uses only the hard-label term. The evaluation split is opened only after the architecture, checkpoint and adult calibration are frozen.

## Quantization and acceptance

Export the best frozen checkpoint to opset 17 FP32 ONNX and validate it with ONNX checker and ONNX Runtime. Quantize with ONNX Runtime static QDQ S8S8 using only the adult calibration split. Do not quantize the 523 MB teacher or merely quantize its linear classifier.

The INT8 model is integrable only if all gates pass on the held-out adult evaluation split:

- Raw FP32/INT8 top-1 agreement is reported. Among samples where both models have a top-1 probability margin of at least 0.10, agreement is at least 99%; every lower-margin disagreement is unavailable/uncertain to the Android policy.
- Mean absolute difference between FP32 and INT8 softmax probabilities is at most 0.02.
- INT8 macro-F1 is no more than one percentage point below FP32 macro-F1.
- Output tensors are finite and shapes are exactly `[batch, 64]` and `[batch, 20]`.

Model accuracy values remain adult engineering measurements, not child accuracy.

## Adult calibration and reference artifact

The calibration split produces per-target engineering evidence from target probability, target margin, entropy and cosine similarity against student reference centroids. Up to 32 speaker-distinct train embeddings per target form the compact reference bank. A target without adequate reference coverage is unavailable.

Threshold selection is deterministic and reports coverage, false-match rate, target recall, `OTHER` rejection and uncertainty coverage. The Android result domain is exactly:

- `DEV_MATCH`: evidence is at or above the frozen high band.
- `DEV_TRY_AGAIN`: adequate evidence is at or below the frozen low band.
- `DEV_UNCERTAIN`: evidence lies between the bands or evidence families disagree.
- `DEV_UNAVAILABLE`: quality, VAD, target, artifact, runtime, or integrity evidence is missing.

These values never become PASS/RETRY and are not persisted as child correctness.

## Bundle

`bundle.json` is canonical JSON and binds:

- `mobile_word_student.int8.onnx`
- `labels.json`
- `reference_bank.json`
- `adult_engineering_calibration.json`
- `silero_vad.onnx`

It records schema/model/vocabulary/preprocessing/VAD/calibration/reference versions, ordered labels, input/output names and shapes, creation time, source hashes, evaluation summary, `approved_for_child_scoring: false`, and SHA-256 for every file. The build fails if a hash changes after manifest creation.

## Android integration

Android uses `com.microsoft.onnxruntime:onnxruntime-android:1.30.0`. `MobileBundleLoader` streams packaged assets, verifies SHA-256 before session creation, and constructs CPU sessions. NNAPI is not enabled. `MobileWordPracticeEngine.assess` runs on `Dispatchers.Default/IO`, applies capture checks and VAD, preprocesses PCM, runs INT8 inference, fuses the frozen adult calibration and returns `LocalWordOutcome` with official `decision = UNSCORABLE`, null `wordMatchProbability`, and a separate nullable `developmentResult` plus non-child-facing evidence fields.

`PracticeScreen` owns a generation token. Break, Stop, navigation disposal, and a new capture invalidate the token, cancel recording/speech, and ignore late inference. Result copy explicitly says “Development check” and never shows a numeric accuracy. `DEV_MATCH` celebrates practice, `DEV_TRY_AGAIN` coaches another whole-word attempt, `DEV_UNCERTAIN` asks for a fresh recording, and `DEV_UNAVAILABLE` explains the technical/capture reason neutrally.

The debug APK may initialize the student. Release builds do not initialize it. There is no HTTP or FastAPI fallback.

## Verification evidence

Required evidence includes deterministic dataset inventory, training history, frozen checkpoint hash, FP32 and INT8 hashes/sizes, quantization parity JSON, adult evaluation JSON, bundle integrity test, Python/Kotlin preprocessing golden parity, JVM tests, Android lint/build, emulator installation/start, airplane/offline microphone attempt, repeated latency samples, cancellation during processing, log inspection for network/model failures, screenshots, final APK size and SHA-256. Physical-device thermal and NNAPI evidence remains pending unless a physical device is actually attached.
