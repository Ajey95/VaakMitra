# Android Local Word Capture Implementation Plan

> **For agentic workers:** Execute inline in this task. The user asked for no sub-agents and no further approval pauses. Each task uses a failing test before implementation.

**Goal:** Remove the broken Android word-audio upload path and provide bounded, in-memory local word practice that abstains until an on-device student exists.

**Architecture:** `WordPcmRecorder` owns Android microphone resources; `LocalWordPractice` owns pure capture validation and a typed no-score outcome. `PracticeScreen` prompts, records, assesses locally, wipes PCM, and offers retry/exit without backend calls or fabricated progress.

**Tech Stack:** Kotlin, Android AudioRecord, Compose, JUnit 4, Gradle.

**Spec:** `docs/superpowers/specs/2026-09-15-android-local-word-capture-design.md` and `VAAKMITRA_FINAL_SSOT.md` v3.3.1.

## Global Constraints

- DEC-013: child-session audio and scoring run locally; no FastAPI/cloud/RTX dependency.
- AU-002/003: mono 16-kHz PCM, bounded capture; this slice caps at eight seconds.
- FUS-007: missing student/calibration means `UNSCORABLE` with null correctness score.
- PRV-001/002: no audio file, network upload, transcript log, or fabricated progress.
- Preserve the existing candle game and unrelated account/catalog screens.

---

### Task 1: Pure local outcome contract

**Files:** Create `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/audio/LocalWordPractice.kt`; test `SpeakEasyAndroid/app/src/test/java/com/team96/speakeasy/audio/LocalWordPracticeTest.kt`.

**Interfaces:** `assess(targetWord: String, samples: ShortArray, sampleRate: Int = 16000): LocalWordOutcome`, where outcome includes `decision`, `reason`, and nullable `wordMatchProbability` but never mutates progress.

- [x] Write tests proving zero/short/clipped/silent input abstains and valid PCM also abstains with `MODEL_UNAVAILABLE` and null score.
- [x] Run `gradlew.bat :app:testDebugUnitTest` and confirm the new tests fail because the interface is absent.
- [x] Implement bounded pure validation and null-score outcome.
- [x] Rerun the unit suite and confirm the tests pass.

### Task 2: Bounded in-memory PCM recorder

**Files:** Create `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/audio/WordPcmRecorder.kt` and pure buffer `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/audio/BoundedPcmBuffer.kt`; test `SpeakEasyAndroid/app/src/test/java/com/team96/speakeasy/audio/BoundedPcmBufferTest.kt`.

**Interfaces:** `BoundedPcmBuffer(maxSamples=128000).append(samples, count)`, `takeAndClear(): ShortArray`; `WordPcmRecorder.start(): Boolean`, `stop(): ShortArray`, `cancel()`, all idempotent where appropriate.

- [x] Write buffer tests for exact cap, oversize truncation, and clearing; confirm RED.
- [x] Implement buffer and verify GREEN.
- [x] Add `AudioRecord` wrapper with `finally` resource release and a bounded reader thread; verify Android compilation.

### Task 3: Word screen migration

**Files:** Modify `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/ui/screens/PracticeScreen.kt`, `.../viewmodel/AppViewModel.kt`, and `.../data/ApiService.kt`.

**Interfaces:** Word screen calls only `WordPcmRecorder` and `LocalWordPractice` for attempts; no `AppViewModel.evaluate`, Retrofit multipart word assessment, progress save, stars, or accuracy UI.

- [x] Add a test for the local result wording/decision mapping and confirm RED before production edits.
- [x] Replace AAC/upload evaluation with local PCM assessment and wipe samples in `finally`; remove unreviewed live Tamil TTS until approved audio assets are packaged.
- [x] Remove obsolete word-upload method and misleading score overlay; keep retry/exit and clear no-score state.
- [x] Run Android unit tests and `:app:assembleDebug`, then inspect the built APK and record hash/size. No device pass is claimed without an attached phone.

### Task 4: Handoff

**Files:** Update `docs/VERIFICATION_STATUS.md` and `docs/BACKEND_COMPLETION_CONTEXT.md`.

- [x] Record exact test/build outcomes, remaining student-model and device gaps, and confirm `git diff --check`.
