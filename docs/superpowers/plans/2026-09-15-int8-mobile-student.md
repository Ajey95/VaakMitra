# VaakMitra INT8 Mobile Student Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Train, statically quantize, package, and integrate the approved 19-word-plus-`OTHER` adult-engineering student into the fully offline Android review APK.

**Architecture:** A reproducible Python pipeline inventories the frozen adult corpus, trains a compact raw-waveform depthwise CNN with hard labels and teacher soft targets, exports FP32 ONNX, produces QDQ S8S8 INT8, calibrates separate `DEV_*` bands, and emits a hash-bound bundle. Android verifies the bundle, runs VAD and word inference off the UI thread, preserves official `UNSCORABLE` semantics, and cancels stale work on Break/Stop.

**Tech Stack:** Python 3.10, PyTorch 2.3, ONNX 1.22, ONNX Runtime 1.22 training/export tooling, NumPy, pytest, Kotlin/JVM 17, Jetpack Compose, ONNX Runtime Android 1.30.0, Gradle.

**Spec:** `docs/superpowers/specs/2026-09-15-int8-mobile-student-design.md`

## Global Constraints

- Normative IDs are DEC-028 and MST-001..010 plus the IDs cited by the spec.
- The target device baseline is Android 10+, ARM64 and 4 GB RAM; CPU is mandatory and NNAPI is disabled.
- Input is 32,000 float32 samples at 16 kHz; outputs are 64 embedding values and 20 logits.
- Training/calibration/evaluation splits are speaker-disjoint and child material is excluded.
- The Android outcome remains official `UNSCORABLE` with null `word_match_probability`; only separate `DEV_*` review evidence is shown.
- Missing or changed bundle files fail closed with no cloud/server fallback.
- Existing user changes and protected VaakMitra roots are not modified.

---

### Task 1: Reproducible mobile dataset and teacher-target index

**Files:**
- Create: `backend/app/vaakmitra_word/mobile_student_data.py`
- Create: `backend/tests/vaakmitra_word/test_mobile_student_data.py`
- Create: `backend/scripts/model/prepare_mobile_student_data.py`

**Interfaces:**
- Produces: `MobileSample`, `load_mobile_samples(...)`, `preprocess_pcm(...)`, `TeacherTargetIndex`, and `mobile-student-data.jsonl`.

- [x] **Step 1: Write failing tests** for ordered 19+`OTHER` labels, exact 32,000-sample centre crop/symmetric pad, target/OTHER mapping, speaker-disjoint partitions, missing audio rejection, and child-root exclusion using literal fixtures.
- [x] **Step 2: Run** `python -m pytest backend/tests/vaakmitra_word/test_mobile_student_data.py -q` and confirm failures name missing interfaces.
- [x] **Step 3: Implement** immutable sample dataclasses, manifest parsing, path/hash validation, PCM decoding/resampling, deterministic preprocessing and teacher-target lookup from the frozen embedding shards/classifier.
- [x] **Step 4: Run the focused test** and the existing corpus/classifier tests until green.
- [x] **Step 5: Execute the preparation script** against the frozen inputs and write inventory/hash evidence under `D:\VaakMitraData\artifacts\mobile-student-ta19-v0\evidence`.

### Task 2: Compact raw-waveform network and deterministic trainer

**Files:**
- Create: `backend/app/vaakmitra_word/mobile_student_model.py`
- Create: `backend/tests/vaakmitra_word/test_mobile_student_model.py`
- Create: `backend/scripts/model/train_mobile_student.py`

**Interfaces:**
- Consumes: `MobileSample`, preprocessed 32,000-sample tensors and optional 20-class teacher probabilities.
- Produces: `MobileWordStudent.forward(waveform) -> (embedding, logits)` and `mobile_word_student.pt`.

- [x] **Step 1: Write failing tests** that require `[B,64]` finite unit-length embeddings, `[B,20]` logits, deterministic seeded output, the exact hard-plus-distillation loss, and gradient flow through real model parameters.
- [x] **Step 2: Run** `python -m pytest backend/tests/vaakmitra_word/test_mobile_student_model.py -q` and confirm failure because the model module is absent.
- [x] **Step 3: Implement** the strided Conv1d stem, four residual depthwise-separable blocks, global pooling, 64-dimensional projection, classification head and the weighted CE/KL loss.
- [x] **Step 4: Run focused tests**, then a one-batch overfit smoke that must reduce loss on a literal fixture.
- [x] **Step 5: Train on the RTX 4060** with deterministic seed, balanced sampling and train-only augmentation; save best checkpoint, history, configuration and hashes without reading the evaluation split.

### Task 3: ONNX export and static INT8 quantization

**Files:**
- Create: `backend/app/vaakmitra_word/mobile_student_export.py`
- Create: `backend/tests/vaakmitra_word/test_mobile_student_export.py`
- Create: `backend/scripts/model/export_mobile_student.py`

**Interfaces:**
- Consumes: frozen checkpoint and calibration-partition waveforms.
- Produces: `mobile_word_student.fp32.onnx`, `mobile_word_student.int8.onnx`, and `quantization-parity.json`.

- [x] **Step 1: Write failing tests** for the exact ONNX input/output names and shapes, finite ORT output, calibration-reader exhaustion/reset, low-margin abstention, and gate rejection for actionable-region agreement below 0.99, probability MAE above 0.02, or macro-F1 loss above 0.01.
- [x] **Step 2: Run** `python -m pytest backend/tests/vaakmitra_word/test_mobile_student_export.py -q` and confirm the missing export API is the failure.
- [x] **Step 3: Implement** opset-17 export, ONNX checking, FP32 ORT comparison, QDQ S8S8 static quantization and literal acceptance-gate evaluation.
- [x] **Step 4: Run focused tests** and verify a temporary real exported model executes in ORT.
- [x] **Step 5: Export/quantize the trained checkpoint**, evaluate only now on the frozen adult evaluation split, and stop integration if any gate fails.

### Task 4: Adult engineering calibration, references and bundle integrity

**Files:**
- Create: `backend/app/vaakmitra_word/mobile_student_bundle.py`
- Create: `backend/tests/vaakmitra_word/test_mobile_student_bundle.py`
- Create: `backend/scripts/model/build_mobile_student_bundle.py`

**Interfaces:**
- Produces: `MobileCalibration`, `evaluate_development_result(...)`, `verify_bundle(...)`, and the five-file JSON/ONNX bundle plus `bundle.json`.

- [x] **Step 1: Write failing tests** for speaker-distinct reference selection, literal `DEV_MATCH`/`DEV_TRY_AGAIN`/`DEV_UNCERTAIN`/`DEV_UNAVAILABLE` branches, canonical manifest hashing, tampered-file rejection, unknown-target rejection and `approved_for_child_scoring=false`.
- [x] **Step 2: Run** `python -m pytest backend/tests/vaakmitra_word/test_mobile_student_bundle.py -q` and confirm it fails for the absent bundle API.
- [x] **Step 3: Implement** reference centroid selection, deterministic adult-band fitting, evidence fusion, canonical JSON hashing and full-file integrity verification.
- [x] **Step 4: Run focused tests** plus a mutation check that changes one model byte and must reject the bundle.
- [x] **Step 5: Build the immutable bundle**, re-verify it from disk and copy only the runtime files into `SpeakEasyAndroid/app/src/main/assets/vaakmitra/mobile-student-ta19-v0/`.

### Task 5: Android preprocessing and verified bundle loader

**Files:**
- Modify: `SpeakEasyAndroid/app/build.gradle.kts`
- Modify: `SpeakEasyAndroid/app/proguard-rules.pro`
- Create: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/audio/MobileBundleLoader.kt`
- Create: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/audio/MobilePcmPreprocessor.kt`
- Create: `SpeakEasyAndroid/app/src/test/java/com/team96/speakeasy/audio/MobileBundleLoaderTest.kt`
- Create: `SpeakEasyAndroid/app/src/test/java/com/team96/speakeasy/audio/MobilePcmPreprocessorTest.kt`

**Interfaces:**
- Produces: `MobilePcmPreprocessor.prepare(ShortArray): FloatArray` and `MobileBundleLoader.load(context): LoadedMobileBundle`.

- [x] **Step 1: Add failing JVM tests** using the Python-generated literal golden vector and a temporary asset source whose missing/tampered files must return typed `MODEL_UNAVAILABLE` failures.
- [x] **Step 2: Run** `gradlew.bat :app:testDebugUnitTest --tests "*MobilePcmPreprocessorTest" --tests "*MobileBundleLoaderTest"` and confirm missing production types cause the failures.
- [x] **Step 3: Add ONNX Runtime Android 1.30.0**, preservation rules, exact PCM conversion/pad/crop code, canonical manifest parsing and streaming SHA-256 verification.
- [x] **Step 4: Run focused JVM tests** and confirm Python/Kotlin preprocessing parity to the committed literals.

### Task 6: Android local VAD, INT8 scorer and fail-closed evidence fusion

**Files:**
- Create: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/audio/OnnxSpeechVad.kt`
- Create: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/audio/OnnxMobileWordStudent.kt`
- Create: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/audio/MobileDevelopmentPolicy.kt`
- Modify: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/audio/LocalWordPractice.kt`
- Create: `SpeakEasyAndroid/app/src/test/java/com/team96/speakeasy/audio/MobileDevelopmentPolicyTest.kt`
- Modify: `SpeakEasyAndroid/app/src/test/java/com/team96/speakeasy/audio/LocalWordPracticeTest.kt`

**Interfaces:**
- Produces: suspend `MobileWordPracticeEngine.assess(targetId, samples, sampleRate): LocalWordOutcome` with official `UNSCORABLE` plus separate development evidence.

- [x] **Step 1: Add failing tests** for every `DEV_*` branch, target-ID lookup, VAD/session failure, non-finite output, missing/tampered bundle, release-disabled mode and the invariant that official probability is always null.
- [x] **Step 2: Run the focused JVM tests** and verify expected failures against the existing `MODEL_UNAVAILABLE` stub.
- [x] **Step 3: Implement** fresh-capture Silero state, INT8 ORT inference, stable softmax/cosine calculations, calibration fusion, buffer clearing and typed failure mapping with injected real interfaces instead of framework mocks.
- [x] **Step 4: Run focused and full JVM tests** and verify all earlier capture-quality behavior remains green.

### Task 7: Compose lifecycle, cancellation and truthful development UI

**Files:**
- Modify: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/ui/screens/PracticeScreen.kt`
- Create: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/audio/AttemptGeneration.kt`
- Create: `SpeakEasyAndroid/app/src/test/java/com/team96/speakeasy/audio/AttemptGenerationTest.kt`

**Interfaces:**
- Consumes: `MobileWordPracticeEngine`.
- Produces: cancellation-safe practice flow and separate engineering-result presentation.

- [x] **Step 1: Write failing tests** showing a Break/Stop/new-capture generation invalidates a late result and that `DEV_MATCH` UI copy contains neither PASS nor accuracy language.
- [x] **Step 2: Run focused tests** and confirm failure against the absent generation guard/new presentation mapping.
- [x] **Step 3: Implement** a remembered engine, background suspend assessment, generation invalidation on every cancellation boundary, immediate recorder/speaker stop, avatar state mapping and calm `DEV_*` overlays.
- [x] **Step 4: Run all Android unit tests**, then `:app:lintDebug` and `:app:assembleDebug`.

### Task 8: Offline emulator and final artifact verification

**Files:**
- Create: `scripts/android/verify_mobile_student.ps1`
- Modify: `docs/VERIFICATION_STATUS.md`
- Create: `docs/evidence/mobile-student-ta19-v0/verification.json`

**Interfaces:**
- Produces: verified APK, screenshots, latency evidence and final SHA-256.

- [x] **Step 1: Add an executable verification script** that rechecks bundle hashes, runs Python and Android tests, lints/builds, installs the APK, starts the activity and records commands/results.
- [x] **Step 2: Run the script with the emulator offline**, capture an Amma microphone attempt, exercise Break during processing, repeat inference for latency samples, and inspect logs for crashes or attempted network fallback.
- [x] **Step 3: Copy the passing APK** to `deliverables/VaakMitra-Mobile-INT8-Review-2026-09-15.apk`, compute SHA-256/size and record emulator/API/ABI plus the explicit evidence limitations.
- [x] **Step 4: Run final clean verification** for Python tests, Android unit tests, lint, assemble, bundle hash, APK install/start and document consistency before claiming completion.
