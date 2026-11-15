# Core Sound Practice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Owner explicitly requested execution now and clarified core/default-ON.

**Goal:** Local core sound-based practice with responsive microphone ownership and no child scoring.
**Architecture:** Separate pure session-memory curricular policy from target-free inference and generic clinical support; reuse current word/result surfaces and closed offline examples. Serialize microphone lifecycle off main with generation invalidation/PCM erasure.
**Tech Stack:** Kotlin/Compose, coroutines1.8.1, JUnit4, Android instrumentation/ORT.
**Spec:** ../specs/2026-11-13-optional-sound-practice-design.md

## Global Constraints

SSOT3.3.60 DEC069/PHN010/MIC001. Core/default-ON, no opt-in switch. Child Skip/Next/pause/Stop retained. No child scores, diagnosis/mastery, raw evidence/counter persistence/uploads, new avatars, reward hooks, fragment recording, cloud/LLM, model/decoder/window changes or1665evaluation repeat. Existing worktree codex/backend-verification-lab, prior dirty work preserved. No commit/push/cleanup.

## Review Focus

- Ambiguous Tamil alignment, gemination, length and variants abstain from specific suggestions.
- Cancel during stalled native start cannot publish a late recording or block UI.
- Cancelled stop erases unpublished PCM and releases controller ownership for retry.
- Every actual recording attempt ages the24-slot history; agreeing labels clear without compacting slots.
- Skip/help state survives idle/result/retry for the same word; warm-up never grants rewards/progression.

### Task1: Sound policy and catalogue

Files audio/SoundPracticePolicy.kt, audio/LocalWordPractice.kt, audio/MobileWordPracticeEngine.kt; test OptionalSoundPracticeTest.kt.
- [x] RED missing API compilation, GREEN8 initial policy tests.
- [x] Closed authored recipes, unique bounded alignment, whole-word variants, transient abstract evidence after inference; generic clinical policy unchanged.
- [x] RED invalid-attempt aging and precise cleared-slot boundary, implement actual-attempt window.
- [ ] Final complete10policy/220total JVM verification.

### Task2: Microphone responsiveness

Files audio/PracticeMicrophone.kt and test PracticeMicrophoneTest.kt; PracticeScreen PREPARING integration.
- [x] RED missing API, GREEN5 initial stalled source/lifecycle tests.
- [x] RED cancelled-stop retry ownership; implement cleanup and PCM erasure.
- [x] Dedicated capture worker, immediate generation invalidation, honest loading/preparing/listening UI. Existing waveform/cap unchanged.
- [ ] Final6microphone/220total JVM verification; owner-tapped hardware feel remains distinct.

### Task3: Core surface and phone delivery

Files ui/components/SoundPracticeCard.kt, PracticeScreen.kt, LocalTamilSpeaker.kt, androidTest SoundPracticeInstrumentedTest.kt.
- [x] Core default-ON sound→syllable→word, explicit help fade/skip, current forward approved related words and core Next prioritization.
- [x] One fresh read-only review0Critical/0Important/2Minor; accepted both and fixed. No re-review.
- [x] All5 actual phone UI checks passed39.757s, including large text and same-word Skip/help retry; prior lookup failure preserved.
- [ ] Final source-complete full JVM/build/lint; install-r, actual APK/model SHA readback; public native parity/privacy and existing round/letter regressions.
- [ ] Verify screenshots, write delivery/context evidence and preserve prior APK/model artifacts.
