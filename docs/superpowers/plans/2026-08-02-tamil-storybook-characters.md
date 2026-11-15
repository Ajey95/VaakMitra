# Tamil Storybook Characters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Pippin and Kavi's 3D characters with friendly animated SVG storybook experiences, including a five-page Tamil Kavi pronunciation journey and local-only Pippin voice echo.

**Architecture:** Pure reducers and scoring helpers define deterministic behavior. React SVG components render character/story state without Canvas or WebGL. Kavi sends bounded audio to a dedicated authenticated Tamil evaluator using acoustic vowel routing and lazy Tamil Whisper ASR; Pippin processes and replays its recording entirely in the browser. Fixed Kavi narration optionally uses an allow-listed server TTS adapter and otherwise falls back to installed `ta-IN` speech synthesis.

**Tech Stack:** React 18, inline SVG, CSS animations, Web Audio, MediaRecorder, FastAPI, librosa, Transformers/Whisper, ElevenLabs optional TTS, Vitest, Pytest, Playwright.

## Global Constraints

- All Kavi child-facing copy, controls, narration, targets, and feedback are Tamil.
- Fixed targets are `அ`, `ஈ`, `அம்மா`, `கவி வா`, and `கவி பாலத்தைக் கடக்கலாம்` in that order.
- No Canvas, WebGL, 3D model, child audio persistence, transcript persistence, or arbitrary child text sent to external TTS.
- Pippin never calls evaluation or upload APIs; it replays the exact in-memory recording locally.
- Calm/minimal motion and `prefers-reduced-motion` preserve readable static character poses.
- Feedback never uses failure, wrongness, diagnosis, or clinical-accuracy language.

---

### Task 1: Tamil story scoring and model routing

**Files:**
- Create: `backend/app/services/tamil_story_evaluator.py`
- Create: `backend/tests/test_tamil_story_evaluator.py`

**Interfaces:**
- Produces: `STORY_TARGETS`, `normalize_tamil(text)`, `score_tamil_transcript(target_id, transcript)`, and `TamilStoryEvaluator.evaluate(audio_bytes, target_id)`.
- Returns: `{accuracy, matched, method, transcript, feedback_key, capability}` with bounded numeric accuracy and finite feedback keys.

- [ ] **Step 1: Write failing pure tests** proving Tamil punctuation/space normalization, fixed target order, vowel routing for `a`/`ii`, token/edit scoring for the word/phrase/sentence, rejection of unknown target IDs, and `model_unavailable` instead of a fabricated score.
- [ ] **Step 2: Run `python -m pytest tests/test_tamil_story_evaluator.py -q`** and confirm the missing-module failure.
- [ ] **Step 3: Implement the target table and pure normalizer/scorer**, using target IDs `a`, `ii`, `amma`, `kavi_vaa`, and `kavi_bridge`; important sentence tokens are `கவி`, `பாலத்தைக்`, and `கடக்கலாம்`.
- [ ] **Step 4: Implement `TamilStoryEvaluator`** with vowel acoustic evaluation for the first two IDs and a lazy `transformers.pipeline("automatic-speech-recognition", model="vasista22/whisper-tamil-small")` adapter for the other three. Never fall back unknown targets to `a`.
- [ ] **Step 5: Run the focused backend test** and confirm all cases pass.

### Task 2: Secure Tamil evaluation and allow-listed story voice endpoints

**Files:**
- Create: `backend/app/services/story_voice.py`
- Create: `backend/app/routers/story_voice.py`
- Modify: `backend/app/routers/evaluation.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`
- Create: `backend/tests/test_tamil_story_routes.py`

**Interfaces:**
- Consumes: `TamilStoryEvaluator.evaluate(audio_bytes, target_id)`.
- Produces: `POST /api/evaluate/tamil-story` with multipart `audio` and `target_id`; `GET /api/story-voice/{line_id}` for finite application-authored Tamil lines.

- [ ] **Step 1: Write failing API/service tests** for authentication, five target IDs, content type, upload size, empty audio, rate-limit dependency, provider-disabled 503, fixed line ID allow-list, and arbitrary line rejection.
- [ ] **Step 2: Run `python -m pytest tests/test_tamil_story_routes.py -q`** and confirm route/service failures.
- [ ] **Step 3: Add the Tamil story evaluation route** reusing the existing audio allow-list, `MAX_UPLOAD_BYTES`, authentication, and rate limiter.
- [ ] **Step 4: Add `StoryVoiceService`** that maps fixed line IDs to Tamil text, calls ElevenLabs only when both server-side key and voice ID exist, sends no user-provided text, and caches returned audio by line ID.
- [ ] **Step 5: Register the story voice router and config fields** without exposing credentials in responses or logs.
- [ ] **Step 6: Run the focused route tests** and confirm all pass.

### Task 3: Pure five-page Kavi story engine

**Files:**
- Create: `frontend/src/features/storybook/kaviStory.js`
- Create: `frontend/src/features/storybook/kaviStory.test.js`

**Interfaces:**
- Produces: `KAVI_STORY_PAGES`, `createKaviStoryState()`, `kaviStoryReducer(state, event)`, `getKaviPage(state)`, and `buildKaviStoryReport(input)`.
- State phases: `intro`, `narrating`, `ready`, `listening`, `evaluating`, `support`, `success`, `walking`, `complete`.

- [ ] **Step 1: Write failing tests** for the exact five Tamil pages, start/narrate/listen/evaluate transitions, gentle retry, support after three attempts, walking progression, completion, and transcript/audio-free reports.
- [ ] **Step 2: Run `npm test -- --run src/features/storybook/kaviStory.test.js`** and confirm the missing-module failure.
- [ ] **Step 3: Implement immutable story data and reducer** with explicit events `START`, `NARRATION_STARTED`, `NARRATION_ENDED`, `LISTEN`, `EVALUATE`, `RESULT`, `USE_HELP`, `WALK_FINISHED`, `NEXT`, and `RESET`.
- [ ] **Step 4: Implement aggregate reporting** with assistance counts only.
- [ ] **Step 5: Run the focused Vitest file** and confirm all cases pass.

### Task 4: Friendly SVG Kavi storybook scene

**Files:**
- Create: `frontend/src/components/storybook/KaviStorybookScene.jsx`
- Modify: `frontend/src/components/interactive/play.css`
- Modify: `frontend/tests/character-coaches.spec.js`

**Interfaces:**
- Consumes props `{pageIndex, mood, message, audioLevel, motionLevel, walkingProgress}`.
- Produces an accessible inline `<svg data-testid="kavi-story-svg">` with named eye, eyelid, mouth, trunk, leg, bridge, family, and scene-layer groups.

- [ ] **Step 1: Change the Kavi browser test first** to require an SVG, reject Canvas/WebGL, assert five story progress points, Tamil text, distinct eye/mouth state attributes, and no speech/control overlap.
- [ ] **Step 2: Run the focused Playwright Kavi test** and confirm it fails against the 3D stage.
- [ ] **Step 3: Implement the SVG scene** with soft flat fills, rounded outlines, page-controlled flower/fireflies/family/bridge layers, and Kavi position derived from walking progress.
- [ ] **Step 4: Add CSS keyframes** for blink, talk, listen, encourage, walk, and celebrate plus full calm/reduced-motion overrides.
- [ ] **Step 5: Run the focused browser test** and confirm the SVG requirements pass.

### Task 5: Local Pippin kitten echo engine

**Files:**
- Create: `frontend/src/features/storybook/kittenEcho.js`
- Create: `frontend/src/features/storybook/kittenEcho.test.js`

**Interfaces:**
- Produces: `createKittenEcho({scope, onLevel})` returning `{play(blob), stop(), dispose()}`.
- `play` resolves after local Web Audio playback; no network dependencies.

- [ ] **Step 1: Write failing tests** with a minimal Web Audio fake proving local decode, playback rate `1.18`, analyser connection, stop/dispose cleanup, original-audio fallback, and zero `fetch`/XHR use.
- [ ] **Step 2: Run `npm test -- --run src/features/storybook/kittenEcho.test.js`** and confirm the missing-module failure.
- [ ] **Step 3: Implement the echo engine** using `AudioContext.decodeAudioData`, `BufferSource`, `GainNode`, `AnalyserNode`, bounded animation frames, and idempotent cleanup.
- [ ] **Step 4: Run the focused echo tests** and confirm all cases pass.

### Task 6: Friendly SVG Pippin repeat-and-play companion

**Files:**
- Create: `frontend/src/components/storybook/PippinStorybook.jsx`
- Modify: `frontend/src/pages/PippinPage.jsx`
- Modify: `frontend/src/components/interactive/play.css`
- Modify: `frontend/tests/character-coaches.spec.js`

**Interfaces:**
- `PippinStorybook` consumes `{mood, audioLevel, motionLevel, message}` and renders `<svg data-testid="pippin-story-svg">`.
- `PippinPage` consumes `useAudioRecorder().audioBlob` and `createKittenEcho` for local replay.

- [ ] **Step 1: Change the Pippin browser test first** to require no Canvas/WebGL, Tamil controls `பேசலாம்`, `முடித்தேன்`, `மீண்டும் சொல்`, `ஆடு`, and `பாடு`, plus animated eye/mouth/tail state markers.
- [ ] **Step 2: Run the focused Pippin browser tests** and confirm they fail against the 3D mission page.
- [ ] **Step 3: Implement the rounded SVG kitten** with separate eyes/eyelids/pupils/smile/talking mouth/scarf/tail groups and deterministic mood attributes.
- [ ] **Step 4: Rewrite PippinPage as a local repeat flow**: record Tamil audio with automatic recognized-repeat disabled, wait for `audioBlob`, replay via the echo engine, retain one in-memory latest blob, and dispose on reset/exit.
- [ ] **Step 5: Add dance and fixed Tamil song controls** using SVG state and local oscillator tones; microphone denial reveals fixed Tamil phrase buttons.
- [ ] **Step 6: Remove Pippin evaluation/mission logic and retain aggregate-only repeat/play reporting.**
- [ ] **Step 7: Run focused unit and browser tests** and confirm all Pippin requirements pass.

### Task 7: Integrate the five-page Tamil Kavi experience

**Files:**
- Replace: `frontend/src/pages/RiverRescuePage.jsx`
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/features/characters/characterVoice.js`
- Modify: `frontend/src/features/characters/characterVoice.test.js`
- Modify: `frontend/src/components/interactive/play.css`

**Interfaces:**
- Adds `evaluationAPI.evaluateTamilStory(formData)` and `storyVoiceAPI.get(lineId)`.
- Adds native Tamil voice selection and mild `kaviTamil` fallback profile.

- [ ] **Step 1: Add failing voice tests** for `ta-IN` preference, mild pitch/rate, Tamil line playback, remote-audio fallback, cancellation, and provider failure.
- [ ] **Step 2: Run the focused voice tests** and confirm the new expectations fail.
- [ ] **Step 3: Implement API wrappers and Tamil voice fallback** without adding arbitrary-text external TTS.
- [ ] **Step 4: Rebuild RiverRescuePage around `kaviStoryReducer`** with Tamil narration, model recording submission, evaluating state, gentle success/retry/help, animated walk, next page, and completion report.
- [ ] **Step 5: Guarantee cleanup** of TTS, object URLs, audio playback, MediaRecorder, recognition, timers, and analyser loops on page/step changes.
- [ ] **Step 6: Run unit tests, lint, and production build** and fix any regressions through systematic debugging.

### Task 8: End-to-end story, privacy, accessibility, and visual verification

**Files:**
- Modify: `frontend/tests/character-coaches.spec.js`
- Modify: `frontend/tests/interactive-accessibility.spec.js` only if route copy selectors changed.
- Create: `docs/qa/tamil-storybook-verification.md`

**Interfaces:**
- Browser API mocks return Tamil evaluator success, low-confidence, support, and capability-unavailable contracts.

- [ ] **Step 1: Complete Playwright journeys** for all five Kavi pages, at least one retry/help turn, Kavi crossing completion, Pippin exact local replay, dance/song, denied microphone fallback, keyboard controls, reduced motion, and 390px mobile layout.
- [ ] **Step 2: Assert privacy boundaries**: Kavi report contains only aggregates; Pippin makes no evaluation/upload request; local/session storage contains no audio/transcript; external voice requests use fixed line IDs only.
- [ ] **Step 3: Run `npm test`, `npm run lint`, `npm run build`, and `npx playwright test`** and record exact results.
- [ ] **Step 4: Run `python -m pytest -q`** and record exact results.
- [ ] **Step 5: Capture desktop and mobile screenshots**, inspect them with `view_image`, and fix clipped Tamil, uncanny shading, character/control overlap, or unclear page changes.
- [ ] **Step 6: Confirm the live frontend and backend remain reachable** and document navigation plus the Tamil model/TTS configuration behavior.

## Self-review

- [x] Every specification section maps to a concrete task: Tamil content, model routing, safe voice, Kavi SVG/story, Pippin SVG/echo/play, privacy, accessibility, fallbacks, reporting, and visual QA.
- [x] All target IDs, Tamil strings, reducer phases, endpoint paths, props, return contracts, and test commands are consistent across tasks.
- [x] No task permits unknown target fallback, arbitrary external TTS text, transcript persistence, raw-audio reporting, punitive copy, Canvas, WebGL, or clinical claims.
- [x] The plan contains no deferred placeholders; optional provider behavior has an explicit native Tamil fallback.
