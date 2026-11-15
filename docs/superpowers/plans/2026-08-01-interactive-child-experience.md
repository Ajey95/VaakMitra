# Interactive Child Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved shared child-interaction engine, sensory/age settings, Voice Arcade, Voice Quest, Mouth Mirror, Pippin, Talk Together, and parent reporting as production-ready web vertical slices.

**Architecture:** A pure reducer and serializable activity definitions own session behavior; focused React feature modules render activities and use capability adapters for microphone, speech synthesis, and face landmarks. FastAPI stores only compact aggregate session summaries and returns authenticated per-user roll-ups. Existing authentication, speech evaluation, game scoring, settings, and parent-dashboard patterns are reused.

**Tech Stack:** React 18, Vite 5, Zustand, TanStack Query, Framer Motion, MediaRecorder/Web Audio/Web Speech APIs, MediaPipe Face Mesh, FastAPI, Pydantic 2, MongoDB, Vitest, Pytest, Playwright.

## Global Constraints

- Primary platform is the React/Vite web application; Android API compatibility is required, but Android feature parity is excluded.
- Every child screen has one primary task and no more than two simultaneous choices.
- Three unsuccessful attempts reveal support and permit progress; no blocking failure screen.
- No raw child audio, video, arbitrary transcript, or facial frame is stored by new features.
- No emotion, stress, attention, or autism-severity inference.
- No unrestricted child-facing generative AI, public child ranking, advertising, purchases, or real-money mechanics.
- Motion, sound, spoken prompts, camera use, and pace remain controllable; `prefers-reduced-motion` is honored.
- All production behavior changes follow red-green-refactor.
- Existing dirty-worktree changes are preserved; commits name only files owned by their task.

---

### Task 1: Pure interactive session engine

**Files:**
- Create: `frontend/src/features/interactive/sessionEngine.js`
- Create: `frontend/src/features/interactive/sessionEngine.test.js`
- Create: `frontend/src/features/interactive/activitySchema.js`
- Create: `frontend/src/features/interactive/activitySchema.test.js`

**Interfaces:**
- Produces: `createSession(activity)`, `sessionReducer(state, event)`, `selectCurrentStep(state)`, `selectProgress(state)`, `validateActivity(activity)`.
- Session state exposes `phase`, `activityId`, `stepIndex`, `attempt`, `hintsUsed`, `effortPoints`, `assistance`, `events`, `startedAt`, and `completedAt`.

- [ ] **Step 1: Write failing reducer and schema tests** covering start, prompt completion, response capture, success, three-attempt support, skip, pause/resume, completion, reset, invalid response modes, and invalid next-step references.
- [ ] **Step 2: Run `npm test -- --run src/features/interactive/sessionEngine.test.js src/features/interactive/activitySchema.test.js`** and verify module-not-found/test failures.
- [ ] **Step 3: Implement the minimal pure reducer and validator** with phases and events defined in the approved spec; timestamps are injected in events so tests stay deterministic.

```js
export function createSession(activity, now = Date.now()) {
  return { phase: 'intro', activity, activityId: activity.id, stepIndex: 0, attempt: 0,
    hintsUsed: 0, effortPoints: 0, assistance: {}, events: [], startedAt: now, completedAt: null }
}
export function sessionReducer(state, event) {
  if (event.type === 'START') return { ...state, phase: 'prompting', events: [...state.events, event] }
  if (event.type === 'PAUSE') return { ...state, phaseBeforePause: state.phase, phase: 'paused' }
  if (event.type === 'RESUME') return { ...state, phase: state.phaseBeforePause || 'ready' }
  return state
}
export function selectCurrentStep(state) { return state.activity.steps[state.stepIndex] }
export function selectProgress(state) { return { current: state.stepIndex + 1, total: state.activity.steps.length } }
export function validateActivity(activity) {
  const errors = !activity?.id || !Array.isArray(activity?.steps) || activity.steps.length === 0
    ? ['Activity requires an id and at least one step'] : []
  return { valid: errors.length === 0, errors }
}
```

- [ ] **Step 4: Re-run the focused tests and then `npm test -- --run`**; expect all tests to pass.
- [ ] **Step 5: Commit only the four task files** with `git commit --only ... -m "feat: add interactive session engine"`.

### Task 2: Versioned sensory and age preferences

**Files:**
- Create: `frontend/src/features/interactive/preferences.js`
- Create: `frontend/src/features/interactive/preferences.test.js`
- Create: `frontend/src/store/interactionSettingsStore.js`
- Create: `frontend/src/components/interactive/SensorySettingsPanel.jsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Produces: `DEFAULT_INTERACTION_PREFERENCES`, `resolveAgeBand(age)`, `migrateInteractionPreferences(raw)`, and Zustand actions `updatePreference`, `setCalmMode`, `resetPreferences`.
- Persisted storage key: `speakeasy-interaction-preferences-v1`.

- [ ] **Step 1: Write failing tests** for age bands 4–6/7–9/10–12, invalid ages, saved-value migration, reduced-motion default selection, and calm-mode overrides.
- [ ] **Step 2: Run the focused preference tests** and verify failures before implementation.
- [ ] **Step 3: Implement preference normalization/store and the caregiver panel** with age band, sound, speech, motion, celebration, contrast, pace, and camera controls.

```js
export const DEFAULT_INTERACTION_PREFERENCES = Object.freeze({
  version: 1, ageBand: 'middle', soundEnabled: true, spokenPrompts: true,
  motionLevel: 'full', celebrationLevel: 'gentle', contrastMode: 'standard',
  sessionPace: 'guided', cameraEnabled: false,
})
export const resolveAgeBand = (age) => age <= 6 ? 'early' : age <= 9 ? 'middle' : 'older'
```

- [ ] **Step 4: Add CSS selectors** for reduced/minimal motion, high contrast, visible focus, and 44 px minimum interactive targets; run all frontend tests.
- [ ] **Step 5: Commit only task-owned files** with message `feat: add child interaction preferences`.

### Task 3: Secure interactive-session reporting API

**Files:**
- Create: `backend/app/models/interactive_session.py`
- Create: `backend/app/routers/interactive_sessions.py`
- Create: `backend/tests/test_interactive_sessions.py`
- Modify: `backend/app/main.py`
- Modify: `frontend/src/services/api.js`

**Interfaces:**
- `POST /api/interactive-sessions` consumes `InteractiveSessionCreate` with `activity_id`, `activity_type`, ISO timestamps, counts, assistance counts, duration, effort points, and optional `game_score_id`.
- `GET /api/interactive-sessions/summary` produces `sessions_this_week`, `communication_turns`, `independent_percentage`, `most_practised_activity`, `assistance_trend`, and `recommendation`.
- Frontend produces `interactiveSessionsAPI.create(data)` and `.summary()`.

- [ ] **Step 1: Write failing Pytest tests** for missing authentication, ownership, range validation, rejection of `audio`, `video`, `transcript`, and `frames`, safe insertion, truthful empty summary, and correct aggregation.
- [ ] **Step 2: Run `python -m pytest tests/test_interactive_sessions.py -q`** and verify import/route failures.
- [ ] **Step 3: Implement strict Pydantic models (`extra="forbid"`), authenticated routes, Mongo indexes, serialization, and router registration.** Never accept a client-provided user ID.

```python
class InteractiveSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activity_id: str = Field(min_length=1, max_length=80)
    activity_type: Literal["arcade", "quest", "mouth_mirror", "pippin", "talk_together"]
    communication_turns: int = Field(ge=0, le=100)
    successful_turns: int = Field(ge=0, le=100)
    attempts: int = Field(ge=0, le=300)
    duration_ms: int = Field(ge=0, le=3_600_000)
```

- [ ] **Step 4: Run focused and full backend tests**; also repair the existing Python 3.12 rate-limit tests to use `asyncio.run` if they still fail for only that compatibility reason.
- [ ] **Step 5: Add the frontend API wrapper and commit only owned files** with message `feat: store private interactive session summaries`.

### Task 4: Child activity home and reusable session shell

**Files:**
- Create: `frontend/src/pages/InteractiveHomePage.jsx`
- Create: `frontend/src/components/interactive/InteractiveSessionShell.jsx`
- Create: `frontend/src/components/interactive/VisualSchedule.jsx`
- Create: `frontend/src/components/interactive/ChildFeedback.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/layout/DashboardLayout.jsx`

**Interfaces:**
- `InteractiveSessionShell` consumes `title`, `state`, `dispatch`, `children`, `onExit`, and `settings`.
- Routes produced: `/play`, `/play/arcade/breath-balloon`, `/play/quest/river-rescue`, `/play/mouth-mirror`, `/play/pippin`, `/play/together`.

- [ ] **Step 1: Add a failing Playwright smoke test** that authenticates through the existing test fixture/API, opens `/play`, verifies six destinations, opens a child route, toggles calm mode, pauses, resumes, and exits.
- [ ] **Step 2: Run the test and verify the route is missing.**
- [ ] **Step 3: Implement the activity home, shell, stable visual schedule, feedback live region, routes, and a single sidebar entry named `Play & Practice`.**

```jsx
<Route path="/play" element={<ProtectedRoute><InteractiveHomePage /></ProtectedRoute>} />
<Route path="/play/arcade/breath-balloon" element={<ProtectedRoute><BreathBalloonPage /></ProtectedRoute>} />
<Route path="/play/quest/river-rescue" element={<ProtectedRoute><RiverRescuePage /></ProtectedRoute>} />
<Route path="/play/mouth-mirror" element={<ProtectedRoute><MouthMirrorPage /></ProtectedRoute>} />
<Route path="/play/pippin" element={<ProtectedRoute><PippinPage /></ProtectedRoute>} />
<Route path="/play/together" element={<ProtectedRoute><TalkTogetherPage /></ProtectedRoute>} />
```

- [ ] **Step 4: Run frontend unit tests, Playwright smoke test, lint, and build.**
- [ ] **Step 5: Commit only task-owned files** with message `feat: add child play and practice shell`.

### Task 5: Calibrated Breath Balloon Voice Arcade

**Files:**
- Create: `frontend/src/features/interactive/audioLevel.js`
- Create: `frontend/src/features/interactive/audioLevel.test.js`
- Create: `frontend/src/features/arcade/breathBalloonActivity.js`
- Create: `frontend/src/features/arcade/breathBalloonActivity.test.js`
- Create: `frontend/src/pages/BreathBalloonPage.jsx`
- Create: `frontend/src/components/interactive/BalloonScene.jsx`

**Interfaces:**
- Produces `createNoiseCalibrator()`, `normalizeAudioLevel(raw, noiseFloor)`, `scoreTargetControl(samples, min, max)`, and `BREATH_BALLOON_ACTIVITY`.
- Uses existing `useAudioRecorder`, `gamesAPI.submitScore`, and `interactiveSessionsAPI.create`.

- [ ] **Step 1: Write failing tests** for two-second calibration sample aggregation, normalized clamping, target-zone accuracy, extreme-peak nonreward, three-round completion, timeout support, and skip.
- [ ] **Step 2: Run focused tests and observe correct failures.**
- [ ] **Step 3: Implement the audio math and activity definition, then the page with permission fallback, visible mic state, three rounds, 20-second supportive timeout, personal best, and clean media teardown.**

```js
export const normalizeAudioLevel = (raw, noiseFloor) =>
  Math.max(0, Math.min(1, (raw - noiseFloor) / Math.max(0.05, 1 - noiseFloor)))
export const inTargetZone = (level, min = 0.25, max = 0.70) => level >= min && level <= max
export const scoreTargetControl = (samples, min, max) =>
  samples.length ? Math.round(samples.filter((v) => inTargetZone(v, min, max)).length / samples.length * 100) : 0
```

- [ ] **Step 4: Add and run Playwright media-mock coverage** for calibration → play → complete, permission denial, and exit cleanup; run unit/lint/build checks.
- [ ] **Step 5: Commit only task-owned files** with message `feat: add breath balloon voice arcade`.

### Task 6: River Rescue Voice Quest

**Files:**
- Create: `frontend/src/features/quest/riverRescueActivity.js`
- Create: `frontend/src/features/quest/riverRescueActivity.test.js`
- Create: `frontend/src/pages/RiverRescuePage.jsx`
- Create: `frontend/src/components/interactive/QuestScene.jsx`
- Create: `frontend/public/assets/interactive/river-rescue/` production image assets

**Interfaces:**
- Produces `RIVER_RESCUE_ACTIVITY` with five deterministic steps and `getQuestCopy(stepId, ageBand)`.
- Uses `evaluationAPI.evaluateSpeech`, audio-level duration evaluation, caregiver fallback, and session reporting.

- [ ] **Step 1: Write failing tests** for five valid steps, age-band copy, two-choice maximum, forest/river branch resolution, phoneme retry/support, bridge-duration success, and reporting payload.
- [ ] **Step 2: Run focused tests and verify failures.**
- [ ] **Step 3: Generate and inspect cohesive child-safe river, forest, elephant, bridge, and celebration assets; implement the deterministic activity and responsive scene using code-native controls/text.**

```js
export const RIVER_RESCUE_ACTIVITY = {
  id: 'river-rescue', type: 'quest', maxAttempts: 3,
  steps: [
    { id: 'choose-path', responseMode: 'choice', choices: ['forest', 'river'] },
    { id: 'call-elephant', responseMode: 'speech', target: 'a' },
    { id: 'ask-help', responseMode: 'speech', target: 'amma' },
    { id: 'lower-bridge', responseMode: 'airflow', targetDurationMs: 1500 },
    { id: 'celebrate', responseMode: 'choice', choices: ['nandri', 'hooray'] },
  ],
}
```

- [ ] **Step 4: Run unit, Playwright happy-path/fallback, accessibility, lint, and build checks at desktop and mobile viewports.**
- [ ] **Step 5: Commit only quest files/assets** with message `feat: add river rescue voice quest`.

### Task 7: Mouth Mirror without emotion inference

**Files:**
- Create: `frontend/src/features/mouthMirror/mouthGeometry.js`
- Create: `frontend/src/features/mouthMirror/mouthGeometry.test.js`
- Create: `frontend/src/features/mouthMirror/targets.js`
- Create: `frontend/src/pages/MouthMirrorPage.jsx`
- Create: `frontend/src/components/interactive/MouthGuideOverlay.jsx`
- Modify: `frontend/src/hooks/useFaceDetection.js`
- Modify: `frontend/src/pages/TongueTrackingPage.jsx`

**Interfaces:**
- Produces `measureMouthGeometry(landmarks)`, `classifyMouthTarget(geometry, target)`, and five target profiles: `open`, `long_open`, `closed_hum`, `lip_pop`, `rounded`.
- `useFaceDetection` returns only `faceDetected`, `mouthWidth`, `mouthHeight`, `mouthOpenRatio`, and `mouthIsOpen`; it no longer exposes `stressLevel` or `emotion`.

- [ ] **Step 1: Write failing fixture-landmark tests** for all geometry outputs, invalid landmarks, five classifications, and 600 ms hold accumulation.
- [ ] **Step 2: Run focused tests and confirm failures.**
- [ ] **Step 3: Implement pure geometry/classification and the mirror page with caregiver camera gate, local-only frame processing, model-only fallback, and visible recording indicator. Remove emotion/stress UI and claims from existing pages.**

```js
export function measureMouthGeometry(landmarks) {
  if (!Array.isArray(landmarks) || !landmarks[291]) return null
  const width = distance(landmarks[61], landmarks[291])
  const height = distance(landmarks[13], landmarks[14])
  return { mouthWidth: width, mouthHeight: height, mouthOpenRatio: width ? height / width : 0 }
}
export function classifyMouthTarget(geometry, target) {
  const matched = geometry && geometry.mouthOpenRatio >= target.minOpen && geometry.mouthOpenRatio <= target.maxOpen
  return { matched: Boolean(matched), cue: matched ? 'Hold it' : target.cue }
}
```

- [ ] **Step 4: Run focused/full tests, a code search proving `stressLevel` and emotion labels are absent from child analysis, and Playwright camera/fallback flows.**
- [ ] **Step 5: Commit owned files** with message `feat: add privacy-safe mouth mirror`.

### Task 8: Integrate Pippin as a safe companion

**Files:**
- Create: `frontend/src/features/pippin/pippinLogic.js`
- Create: `frontend/src/features/pippin/pippinLogic.test.js`
- Create: `frontend/src/pages/PippinPage.jsx`
- Copy/adapt: `TalkingPet/public/pippin-mascot.png` to `frontend/public/assets/interactive/pippin-mascot.png`

**Interfaces:**
- Produces `matchPippinIntent(text)`, `getPippinResponse(intent, text)`, `appendLocalHistory(history, item)`, and curated intents `jump`, `dance`, `sleep`, `eat`, `hello`, `ball`, plus five Tamil words.
- Server reporting uses only intent/vocabulary identifiers and aggregate counts.

- [ ] **Step 1: Write failing tests** for curated commands, unknown safe repeat, deterministic single-word expansion, five-item history cap, arbitrary-transcript exclusion from reporting, and reset.
- [ ] **Step 2: Run focused tests and verify failures.**
- [ ] **Step 3: Implement the page using existing speech input/output behavior, picture-command fallback, touch/pet reactions, sensory settings, local history, and media cleanup.**

```js
export const PIPPIN_INTENTS = new Set(['jump', 'dance', 'sleep', 'eat', 'hello', 'ball', 'amma', 'appa', 'a', 'aa', 'la'])
export function matchPippinIntent(text) {
  const words = String(text || '').toLowerCase().match(/[\p{L}]+/gu) || []
  return words.find((word) => PIPPIN_INTENTS.has(word)) || 'repeat'
}
export function appendLocalHistory(history, item) { return [item, ...history].slice(0, 5) }
export function toPippinReport(history) { return history.map(({ intent }) => ({ intent })) }
```

- [ ] **Step 4: Run unit, Playwright speech/picture/reset/privacy flows, lint, and build.**
- [ ] **Step 5: Commit owned files/assets** with message `feat: integrate pippin practice companion`.

### Task 9: Talk Together caregiver missions

**Files:**
- Create: `frontend/src/features/together/talkTogetherActivity.js`
- Create: `frontend/src/features/together/talkTogetherActivity.test.js`
- Create: `frontend/src/pages/TalkTogetherPage.jsx`
- Create: `frontend/src/components/interactive/CaregiverPromptPanel.jsx`

**Interfaces:**
- Produces five mission definitions and `summarizeAssistance(events)` returning counts for `independent`, `verbal_prompt`, `visual_prompt`, `modelled`, and `skipped`.

- [ ] **Step 1: Write failing tests** for mission count/content, one child prompt, no media requirement, all assistance levels, advancement, completion, and reporting aggregation.
- [ ] **Step 2: Run focused tests and verify failures.**
- [ ] **Step 3: Implement missions, discreet caregiver panel, deterministic completion, and session submission.**

```js
export const ASSISTANCE_LEVELS = ['independent', 'verbal_prompt', 'visual_prompt', 'modelled', 'skipped']
export function summarizeAssistance(events) {
  return Object.fromEntries(ASSISTANCE_LEVELS.map((level) => [level, events.filter((e) => e.assistance === level).length]))
}
```

- [ ] **Step 4: Run unit and Playwright caregiver-confirmation flows at desktop/mobile widths, then lint/build.**
- [ ] **Step 5: Commit owned files** with message `feat: add talk together missions`.

### Task 10: Real parent interactive-practice reporting

**Files:**
- Create: `frontend/src/components/parent/InteractivePracticeSummary.jsx`
- Create: `frontend/src/features/interactive/parentSummary.js`
- Create: `frontend/src/features/interactive/parentSummary.test.js`
- Modify: `frontend/src/pages/ParentDashboard.jsx`

**Interfaces:**
- Consumes `interactiveSessionsAPI.summary()`.
- Produces truthful loading, error, empty, and populated states plus seven-session assistance trend visualization.

- [ ] **Step 1: Write failing tests** for empty summary, independent percentage, most-practised label, assistance trend order, and recommendation rendering data.
- [ ] **Step 2: Run focused tests and verify failures.**
- [ ] **Step 3: Implement a focused summary component and query integration without fabricated fallback values.**

```jsx
const { data, isLoading, error } = useQuery({
  queryKey: ['interactive-session-summary'],
  queryFn: () => interactiveSessionsAPI.summary().then((response) => response.data),
})
return <InteractivePracticeSummary summary={data} isLoading={isLoading} error={error} />
```

- [ ] **Step 4: Run unit and Playwright test proving a completed Talk Together session appears in Parent Dashboard.**
- [ ] **Step 5: Commit owned files** with message `feat: report interactive practice to parents`.

### Task 11: Security, privacy, accessibility, and code-quality hardening

**Files:**
- Modify: feature files identified by audits only
- Create: `docs/security/interactive-experience-threat-model.md`
- Create: `frontend/tests/interactive-accessibility.spec.js`

**Interfaces:**
- Produces a threat model covering identity/ownership, input validation, child data minimization, media lifecycle, XSS-safe rendering, local-storage limits, denial-of-service bounds, and dependency exposure.

- [ ] **Step 1: Add failing security/accessibility checks** for forbidden payload fields, cross-user access, oversized counts/durations, raw transcript persistence, missing labels, keyboard traps, focus visibility, reduced motion, and leaked media tracks.
- [ ] **Step 2: Run Semgrep-equivalent repository searches and dependency audits** using available local tools: `npm audit --omit=dev`, `pip-audit` if installed, secret filename/status checks, and targeted `rg` searches for unsafe HTML/eval/debug artifacts.
- [ ] **Step 3: Fix only confirmed findings** with focused regression tests before each code change; document accepted residual risks and dependency-only findings.
- [ ] **Step 4: Run frontend lint/build/tests, backend tests, Playwright accessibility suite, and Android `assembleDebug`.**
- [ ] **Step 5: Commit owned hardening files** with message `security: harden interactive child experience`.

### Task 12: Full visual and functional verification

**Files:**
- Create: `docs/qa/interactive-experience-fidelity-ledger.md`
- Create: final temporary screenshots outside tracked source, then remove temporary QA artifacts.

**Interfaces:**
- Produces verified desktop and mobile evidence for Activity Home, Breath Balloon, River Rescue, Mouth Mirror, Pippin, Talk Together, and Parent Dashboard.

- [ ] **Step 1: Start backend/frontend test services and seed an authenticated test account without using production credentials.**
- [ ] **Step 2: Run all unit/API/browser/regression commands** and record exact pass/fail totals; fix every in-scope failure and rerun.
- [ ] **Step 3: Capture desktop and mobile screenshots for every primary state and inspect them with `view_image`; check copy, hierarchy, typography, palette, asset treatment, spacing, focus, motion, and responsive behavior.**
- [ ] **Step 4: Complete the fidelity ledger with at least five concrete comparisons per major surface, remove QA artifacts, run `git diff --check`, and review the final diff for secrets or unrelated files.**
- [ ] **Step 5: Commit only QA documentation** with message `test: verify interactive child experience`.

## Final verification commands

```powershell
Set-Location C:\final_year_project\frontend
npm test -- --run
npm run lint
npm run build
npx playwright test

Set-Location C:\final_year_project\backend
python -m pytest -q

Set-Location C:\final_year_project\SpeakEasyAndroid
.\gradlew.bat assembleDebug
```
