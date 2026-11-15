# Categorized Tamil Alphabet Implementation Plan

> For agentic workers: use superpowers:executing-plans inline task by task. No commits or cleanup in the existing dirty isolated lab.

Goal: make all247 traditional Tamil letters available as categorized offline learning alongside19words.
Architecture: pure TamilAlphabet registry, independent letter route, categorized Lessons browser; existing word inference unchanged.
Tech: Kotlin/Compose, existing Android dependencies/offline Gradle.
Spec: docs/superpowers/specs/2026-11-11-tamil-alphabet-design.md

## Global constraints
SSOT3.3.36 DEC052/016 UX003 PHN004.12/18/1/216symbols, stable IDs, no letter mic/TTS/scoring/training. Preserve protected roots and existing V7/goldens/word IDs. User selected all247categorized, no more design permission needed. Existing local lab/branch stays, no commits/push/cleanup. No new dependencies.

## Review Focus
- All traditional symbols correct, unique and canonically normalized; no Grantha or aytham phoneme invention.
- Uyirmei family navigation reaches all216, including last family/vowel.
- Letter route never reaches word microphone/model/scoring or updates mastery.
- Unknown IDs, back/next and rotation do not silently select another item.
- Small screens/large font remain scrollable;19word routes remain reachable.

## Task1 catalogue + meaningful tests
- [x] Write TamilAlphabetTest.kt: exact12Uyir/18Mei,247unique NFC IDs/symbols, full pinned ka and last na families,216family coverage, invalid/word IDs reject, unchanged19word routes.
- [x] Run testDebugUnitTest RED before implementing TamilAlphabet.kt (LetterGroup/TamilLetter/TamilAlphabet.find/inGroup/next/previous).
- [x] Implement closed catalogue with stable ASCII IDs; test suite GREEN.

## Task2 categorized UI + native regression
- [x] Modify LessonsScreen/HomeScreen/AppNavGraph, add LetterLearningScreen. Four categories+Words, Uyirmei family picker, scrollable grids/details, safe unknown ID, no letter audio/scoring.
- [x] Add native catalogue regression and run full JVM/lint/assemble main+test, native checks, inspect rendered categorized/family/letter UI without microphone.
- [x] Run separate public calibration-only candidate-word probe; suggestions only.

## Task3 one review + delivery
- [x] One fresh whole-scope reviewer; regrade, ONE Important fix pass with regression checks; deferMinor.
- [x] Install/verify physical ARM64 APK when connected, save portable APK, model digest/validation/probe report/context; no recording or model promotion. Preserve branch.

## Scope extension before final review (user explicitly requested)
- [x] Task4 TDD: LetterProgressTest/LetterSessionTest missing-API RED then implement pure reducers in LetterJourney.kt, child/account-scoped LetterJourneyStore.kt and AppViewModel state. Test every sequential boundary, replay/skip/unknown IDs, restoration, terminal, round limit/break/background/session budgets.
- [x] Task5 visual/engagement integration: native Tamil Heritage components + original generated veranda PNG, redesign Home/letter catalogue/letter learning, preserve all frozen avatar/word-session sources and route order. Wire practice completion/unlocking, settings, transient tracing, first/then schedule and pause controls. Existing word UX remains intact. Update native UI tests for available/locked states and persistence using internal debug-only host when necessary; no extra dependencies.
- [x] Task6 final validation and ONE fresh whole-scope review, then ONEImportant TDD fix pass. Build/JVM/native/rendered narrow/large-font checks, no user voice; install hash-verified physical APK, preserve existing V7. Deliver source/proofs/screenshots/model binding and honest word suggestions; no commits/merge/push.

Extension review focus: no unlock bypass/double taps/profile leak; stop/background/timer must win and allow no forced resume; bounded trace RAM/no storage; no regressions in preserved avatars/word-session flow; visual Tamil rendering/large font/contrast and no high motion. Signature visual motifs must survive actual native rendering, with much calmer focused practice than menu artwork.

## Task7 latest user steering — shared voice sessions for all247
- [x] RED closed LetterVoiceSessionTest for all247 lesson/prompt resolution, Aytham name, unknown IDs; RED native missing assessLetter API.
- [x] Extend shared PracticeScreen optional letter target/callbacks; default word flow retained. Validate letter target before waveform-only phoneme preview, no word-classifier fallback. Add on-tap offline system-voice letter preview with explicit unverified captions and mutually-exclusive playback/recording.
- [x] Retain parent locks/rounds/tracing/voluntary breaks/participation summary, and manual confirmation only for unlocking; no child recording in tests.
- [x] Full JVM/lint/build/native including unchanged word goldens, both letters and word session UI, foreground/large-font Stop; then ONE fresh whole-scope review of the final combined request. No final review has yet been dispatched.

## Final review authority update (DEC-056 supersedes earlier no-voice clauses)
All tasks now follow SSOT3.3.39: shared letter voice preview is explicitly authorized, while letter targets never enter the word classifier or word reports. The original Task2/Review Focus no-letter-audio restrictions are historical and superseded. Check default word flow, RAM-only cleanup, cancellation/stale-target boundaries, manual progression, replay/local-next and round pauses. System voice is unverified and Aytham reads its name. Unknown closed IDs abstain. No private recordings or predicted phone strings persist.

Final completion: one fresh review/six Important fixes,100JVM,lint0errors,17native on physical+emulator, current installed APK digests verified. Delivery packaging follows the completed checks; no commit/merge/push/cleanup. See docs/verification/tamil-heritage-20261111.md and analysis final-verification.json.
