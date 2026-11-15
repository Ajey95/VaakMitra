# Pause-aware Alignment and Voice Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Implement inline, with one fresh scoped final review. User explicitly authorized implementation of the previously described approach.

**Goal:** Test timing-tolerant acoustic processing honestly and provide neutral automatic Tamil voice guidance without changing avatars/session flow.
**Architecture:** Target-free pause compaction and CTC decoding; separately bounded posterior/reference alignment and a closed voice-coach policy. Promote acoustic preprocessing only on predeclared paired nonregression; alignment never becomes a forced recognition answer.
**Tech Stack:** Existing Python/numpy/PyTorch CUDA and Kotlin/Compose/offline Tamil TTS. No new dependency/model download.
**Spec:** ../specs/2026-11-13-pause-aware-alignment-design.md

## Global Constraints
SSOT3.3.62 DEC071/PHN012/COA001. No child correctness/clinical approval, no raw private evidence in product persistence, no training/threshold tuning on this cohort, no1665evaluation repeat, no microphone automation. Preserve current avatars/session/clock/reward/privacy behavior. Existing dirty isolated lab; protected roots read-only; no commit/push/cleanup.

## Review Focus
- Quiet consonants and terminal sounds must survive pause processing; no silently truncated long words.
- Alignment must not manufacture expected phones, collapse gemination or count reference-conditioned outputs as recognition.
- Benchmark denominators/labels remain identical; failures and abstentions are not hidden.
- Spoken feedback stops on pause/background/identity change and respects quiet preference.
- Source voice readiness/callback errors cannot hang cue flow or cause replay/capture overlap.

### Task1 — Pure processing and GPU experiment
- [x] Write failing Python tests for conservative pause compaction/time map and posterior sequence alignment (stretched/blank frames, deletion, ambiguity, invalid values).
- [x] Implement backend/app/vaakmitra_word/pause_alignment.py; run focused GREEN tests.
- [x] Freeze GPU script/config/input/model/reference identities in D:/VaakMitraData/analysis/pause-aware-20261113 before inference. Reuse authenticated model reconstruction; verify raw saved baseline and public controls.
- [x] Run paired target-free candidate inference, same73primary evaluation, explicit long/unmapped accounting and timing diagnostics. Keep outputs/metrics separate for raw recognition and target-conditioned support. No parameter search.

### Task2 — Android alignment and interactive coaching
- [x] Write failing Kotlin tests for pause map, alignment and closed neutral cue selection; port pure bounded algorithms with parity fixtures.
- [x] Add transient acoustic frame summaries/diagnostic alignment to native backbone outcome; retain raw decoded phones and official abstention. Gate any waveform change by experiment decision.
- [x] Add closed PracticeCoachCue and cancellable voice-first feedback through LocalTamilSpeaker/runGuideCues in current PracticeScreen. Existing avatars, controls, rounds and focus clocks unchanged.
- [x] Reuse the existing public no-mic autonomous fixtures and add meaningful pure cancellation/quiet-mode/voice-coach tests; full JVM/build/lint passed. New rendered-coach qualification is deferred: no device/emulator is available and the owner deferred physical checks.

### Task3 — Review, proof and report
- [x] Fresh scoped read-only review; fix Critical/Important once with regressions, preserve minor rulings.
- [x] Verify source-stable APK/source/model hashes and available public UI checks. Do not claim owner-deferred physical qualification.
- [x] Record recognition improved/same/regressed with exact paired counts, limitations and active capture decision. Update context/ledger and deliver APK/report without model copies.

Final:implemented and built,255Android+27backendtests andlintpassed. Capture candidate failedstrictimprovement and remainsinactive. Phone/rendered/actualvoicechecksdeferred,notpassed. Allnewartifacts onD; noinstall/deviceforeground/microphoneactivity. SeeD:/VaakMitraData/analysis/pause-aware-20261113/PAUSE_AWARE_DELIVERY_REPORT.md.
