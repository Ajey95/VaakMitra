# Expressive Avatar Android Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mirror the approved avatar identities, preference schema and governed reactions in the native Android Compose app for ordinary mobile devices.

**Architecture:** Pure Kotlin catalogue/presentation functions own validation and state mapping. DataStore persists one child-scoped preference. Compose Canvas renders platform-native vector equivalents of the original SVG identities and animates only named governed poses; scoring remains in the existing word-practice boundary.

**Tech Stack:** Kotlin, Jetpack Compose, DataStore Preferences, JUnit 4, Gradle Android plugin.

**Spec:** `docs/superpowers/specs/2026-09-15-expressive-avatar-library-design.md`

**Execution status (2026-09-15):** Code and build complete through Task 4. JVM tests, `assembleDebug` and `lintDebug` pass; the APK and hash are recorded in `docs/VERIFICATION_STATUS.md`. Task 5 physical-device visual/runtime evidence remains blocked because `adb devices` reports no attached device. The preference store uses the current single-child profile scope with a hashed local key; no image data is stored.

## Global Constraints

- Implement `DEC-013`, `DEC-014`, `DEC-020`, `DEC-025`, and `DEC-026`.
- Android 10+ behavior must remain ARM64/4 GB friendly; no video, WebView or runtime asset download.
- Use the same version-1 preference fields and identifiers as web.
- Compose vector drawing is the native rendering equivalent of the canonical SVG rig.
- No avatar action may change a score, plan boundary, retry limit or stop behavior.

---

### Task 1: Android preference and presentation domain

**Files:**
- Create: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/avatar/AvatarModels.kt`
- Create: `SpeakEasyAndroid/app/src/test/java/com/team96/speakeasy/avatar/AvatarModelsTest.kt`
- Modify: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/data/SessionManager.kt`

**Interfaces:**
- Produces: `AvatarPreference`, `AvatarIdentity`, `AvatarMotion`, `AvatarPhase`, `AvatarPose`, `normalizeAvatarPreference`, and `poseForPhase`.

- [ ] **Step 1:** Write failing JVM tests for defaulting, allowed IDs, per-phase literal poses, and reduced/still motion.
- [ ] **Step 2:** Run `gradlew.bat testDebugUnitTest --tests "*.AvatarModelsTest"` and confirm missing-symbol failure.
- [ ] **Step 3:** Implement pure models and add child-scoped DataStore preference load/save without storing images.
- [ ] **Step 4:** Rerun tests and commit with `git commit -m "feat(android): add avatar preference domain"`.

### Task 2: Native expressive vector renderer

**Files:**
- Create: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/ui/avatar/ExpressiveAvatar.kt`

**Interfaces:**
- Consumes: `AvatarPreference`, `AvatarPhase`, `speaking`, `audioLevel`.
- Produces: a Canvas-based scalable character with face, mouth, brows, head, torso and articulated hands.

- [ ] **Step 1:** Implement deterministic geometry helpers exercised by the pure pose tests; do not add screenshot-only test hooks.
- [ ] **Step 2:** Draw three parameterized human identities and one storybook companion with the approved warm palette, highlights and hand shapes.
- [ ] **Step 3:** Add bounded `animateFloatAsState` transitions and one-shot greeting/celebration transitions; honor motion override.
- [ ] **Step 4:** Run Android unit tests and `assembleDebug`, then commit with `git commit -m "feat(android): render expressive avatar guides"`.

### Task 3: Parent picker and profile integration

**Files:**
- Create: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/ui/avatar/AvatarPicker.kt`
- Modify: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/ui/screens/ProfileScreen.kt`

**Interfaces:**
- Produces: mobile-first `Choose your guide` section with preview, identity, palette, motion and save controls.

- [ ] **Step 1:** Implement a vertically scrolling profile layout so 360–390 dp devices never clip the picker or logout control.
- [ ] **Step 2:** Add a large avatar preview followed by horizontally scrollable identity choices and touch targets at least 48 dp.
- [ ] **Step 3:** Save through `SessionManager` and show the saved guide immediately.
- [ ] **Step 4:** Run `assembleDebug` and commit with `git commit -m "feat(android): add caregiver avatar picker"`.

### Task 4: Practice-session integration

**Files:**
- Modify: `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/ui/screens/PracticeScreen.kt`

**Interfaces:**
- Consumes: saved preference and existing local practice phase.
- Produces: selected guide above the word controls with state mapping and dominant red Break / Stop.

- [ ] **Step 1:** Map idle, recording, processing, result and paused phases to `AvatarPhase` without reading numerical evidence.
- [ ] **Step 2:** Replace the oversized animated letter card with a balanced mobile layout: avatar and prompt first, target word second, mic action third, red stop always visible.
- [ ] **Step 3:** Cancel avatar animation with recorder cancellation and prevent infinite motion in paused/error states.
- [ ] **Step 4:** Run Android unit tests, lint and `assembleDebug`; record APK path and hash.

### Task 5: Device-size visual verification and handoff

**Files:**
- Modify: `docs/VERIFICATION_STATUS.md`
- Modify: `docs/BACKEND_COMPLETION_CONTEXT.md`

**Interfaces:**
- Produces: honest Android build evidence and identified physical-device gates.

- [ ] **Step 1:** If an emulator/device is available, render Profile and Practice at 360x800 and 390x844-equivalent sizes and capture screenshots; otherwise record the exact blocker without claiming runtime proof.
- [ ] **Step 2:** Compare mobile screenshots to the approved direction and repair clipping, weak hierarchy, overly robotic expressions or excessive motion.
- [ ] **Step 3:** Run final Gradle unit tests, lint and debug build; update documentation with exact evidence and remaining physical-device/model gates.
