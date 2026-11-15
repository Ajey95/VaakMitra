# Clean Learner Flow Implementation Plan

> REQUIRED SUB-SKILL: superpowers:executing-plans inline; one final fresh source reviewer, one material RED/GREEN fix pass, no implementer agents or re-review.

**Goal:** Remove learner-facing debug instructions and deliver a verified end-to-end offline review flow.
**Architecture:** Shared entry policy, existing local session identity and avatar/session components, plain presentation copy and a pinned generated-model asset overlay. No scoring/model changes.
**Tech stack:** Existing Kotlin/Compose/DataStore, offline Gradle/SDK/ADB emulator, PowerShell build staging.
**Spec:** ../specs/2026-11-14-clean-learner-flow.md

## Global constraints

SSOT3.3.78 DEC079/UX014; retained baseline only, research on hold, no new games/LLM/clinical scoring/cloud or phone actions. Preserve existing theme/avatars/sessions/locks/rewards/privacy/internal UN­SCORABLE. Output/staging/caches D; C>=512MiB; no source/model/data deletion or recursive cleanup. Prior APK rollback retained.

## Review focus

- Local practice must not masquerade as backend authentication or leak its local marker into HTTP.
- First-time and returning entry/back-stack flows must not bypass setup or trap a learner.
- Removing debug copy must not manufacture correct-speech, mastery, saved-report or therapist-booking claims.
- Word/letter session lifecycle/audio/reward behavior and public test fixture isolation must remain intact.
- Fresh offline APK installation must contain/authenticate the retained model, not depend on PC provisioning or expose a rejected variant.

### Task1: Entry and user-facing cleanup

- [x] Add meaningful entry-policy and presentation regression tests RED; implement shared routing and normal local-start/error handling, then GREEN.
- [x] Replace technical copy throughout onboarding/login/home/lessons/practice/summary/progress/rewards/profile/checkup/caregiver and emitted local outcomes; preserve data/gates/avatar/session logic.
- [x] Add authentic main-activity emulator flow/technical-text regression tests and update affected visible-copy expectations without weakening model/privacy assertions.

### Task2: Offline build and review

- [x] Add pinned model asset overlay and D-only reproducible build script; verify metadata/hash/size and retain previous artifacts.
- [x] Run offline JVM/lint/build checks. One final fresh source review, one material fix pass with regression tests; no re-review.

### Task3: End-to-end evidence and delivery

- [x] Build both review ABIs and test APK; use isolated emulator data, install only on emulator.
- [x] Verify authentic fresh/returning local flow, word/letter sessions, guide choice, help/break/end/reward/summary/progress/profile/back navigation and no technical copy; inspect screenshots and real baseline inference.
- [x] Record exact APK/source/model hashes, test outcomes/limits; update context/ledger and provide final APK. No physical-device claim or production/clinical readiness.
