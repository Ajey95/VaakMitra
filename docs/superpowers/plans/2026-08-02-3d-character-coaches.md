# 3D Character Coaches Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn Pippin and Kavi into responsive, original 3D child coaches with safe voices, clear call-and-response turns, multimodal fallback, sensory settings, and privacy-preserving progress counts.

**Architecture:** Keep child interaction deterministic and local. A pure character voice module owns safe speech profiles and installed-voice selection; a pure coach module owns Pippin's mission state. A procedural React Three Fiber stage renders original kitten/elephant characters without remote assets, with a static fallback when WebGL is unavailable. Existing session/reporting APIs continue receiving aggregate counts only.

**Tech Stack:** React 18, Zustand, Three.js, React Three Fiber, Web Speech APIs, Vitest, Playwright, ESLint, Vite.

---

## Task 1: Add safe character voice profiles

**Files:**
- Create: `frontend/src/features/characters/characterVoice.js`
- Test: `frontend/src/features/characters/characterVoice.test.js`

- [ ] Write failing tests for the `kitten`, `gentle`, and `kavi` profiles, guided pacing, unknown-profile fallback, clamping, and installed voice preference order.
- [ ] Run `npm test -- --run src/features/characters/characterVoice.test.js` and confirm the missing-module failure.
- [ ] Implement `VOICE_PROFILES`, `getVoiceProfile`, `selectInstalledVoice`, `createCharacterUtterance`, `speakCharacter`, and `stopCharacterSpeech` using an allow-list and no remote voice service.
- [ ] Run the focused voice tests and confirm they pass.

## Task 2: Persist only an allow-listed Pippin voice preference

**Files:**
- Modify: `frontend/src/features/interactive/preferences.js`
- Modify: `frontend/src/features/interactive/preferences.test.js`

- [ ] Add a failing migration test proving `pippinVoice: 'kitten' | 'gentle'` persists and invalid values become `kitten`.
- [ ] Run the focused preference test and confirm the failure.
- [ ] Add `pippinVoice` to defaults and enum migration without changing calm-mode semantics.
- [ ] Run the focused preference test and confirm it passes.

## Task 3: Add the deterministic Pippin coach engine

**Files:**
- Create: `frontend/src/features/characters/characterCoach.js`
- Test: `frontend/src/features/characters/characterCoach.test.js`

- [ ] Write failing tests for five mission prompts, accepted voice/picture responses, retry/support escalation, skip without punishment, next-mission progression, and completion.
- [ ] Run the focused coach tests and confirm the missing-module failure.
- [ ] Implement immutable mission data plus `createCoachState`, `characterCoachReducer`, and `getCoachMission` with explicit events only.
- [ ] Run the focused coach tests and confirm they pass.

## Task 4: Build the procedural 3D character stage and fallback

**Files:**
- Create: `frontend/src/components/interactive/CharacterStage3D.jsx`
- Create: `frontend/src/features/characters/webglSupport.js`
- Test: `frontend/src/features/characters/webglSupport.test.js`
- Modify: `frontend/src/components/interactive/play.css`

- [ ] Write failing tests for WebGL capability detection and forced fallback.
- [ ] Run the focused test and confirm the missing-module failure.
- [ ] Implement procedural kitten and elephant geometry, eyes, mouth, ears/trunk, scarf, mood-driven motion, capped DPR, accessible status text, reduced-motion handling, and a static image fallback.
- [ ] Add responsive stage styles with keyboard focus, no horizontal overflow, and calm-mode motion suppression.
- [ ] Run focused tests, lint the new modules, and build the frontend.

## Task 5: Turn Pippin into a five-turn interactive coach

**Files:**
- Modify: `frontend/src/pages/PippinPage.jsx`
- Modify: `frontend/src/components/interactive/play.css`

- [ ] Integrate `characterCoachReducer` and map phases to `idle`, `speaking`, `listening`, `thinking`, `encourage`, and `celebrate` moods.
- [ ] Replace the static mascot button with `CharacterStage3D` while keeping an explicit pat control and fallback image.
- [ ] Add Cute Kitten/Gentle voice controls backed by the allow-listed preference and shared speech helper.
- [ ] Add Start, replay prompt, microphone, picture response, try-again, skip, and next controls; every flow must remain usable without a microphone.
- [ ] Preserve local-only transcript history and counts-only server reporting.
- [ ] Run unit tests, lint, and build.

## Task 6: Make Kavi the speaking River Rescue guide

**Files:**
- Modify: `frontend/src/pages/RiverRescuePage.jsx`
- Modify: `frontend/src/components/interactive/QuestScene.jsx`
- Modify: `frontend/src/components/interactive/play.css`

- [ ] Replace direct speech synthesis with the shared `kavi` voice helper and cancel speech on prompt changes/unmount.
- [ ] Embed the procedural Kavi stage in `QuestScene` and map quest modes to character moods.
- [ ] Keep all five existing voice, choice, airflow, picture-help, retry, and completion paths intact.
- [ ] Run quest tests, lint, and build.

## Task 7: Prove child interaction and accessibility in the browser

**Files:**
- Create: `frontend/tests/character-coaches.spec.js`
- Modify if required: `frontend/playwright.config.js`

- [ ] Add mocked-auth browser tests for Pippin mission start, picture response, next mission, voice profile pitch/rate, pat reaction, Kavi rendering, Kavi choice reaction, reduced motion, WebGL/static fallback, keyboard controls, and mobile overflow.
- [ ] Run `npx playwright test tests/character-coaches.spec.js` and fix failures through the systematic-debugging workflow.
- [ ] Run the full frontend unit test, lint, build, and Playwright suites.
- [ ] Run backend tests to ensure reporting/auth remain stable.
- [ ] Perform a final live smoke check on the already running application and document navigation paths and honest limits (automated simulation is not a substitute for supervised testing with children).

## Self-review

- [x] Every design requirement maps to an implementation task: voice, coach state, 3D, fallback, sensory preferences, privacy, Pippin, Kavi, and browser verification.
- [x] All new state and profile values are explicit and allow-listed; there are no placeholders or open-ended child dialogue.
- [x] The plan preserves existing reporting interfaces and does not add raw audio or transcript storage.
- [x] Verification covers unit, accessibility, responsive browser, build, lint, backend regression, and live smoke checks.
