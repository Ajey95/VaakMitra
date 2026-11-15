# Pippin Bilingual Hands-Free Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bilingual English–Tamil Pippin that requests microphone permission once, automatically ends a child's turn after 3.5 seconds of silence, replays it locally in a bright kitten-style voice, and listens again without Start/Stop buttons.

**Architecture:** Keep audio private in the browser. Add a pure, deterministic voice-turn detector beside the existing storybook audio code; make `PippinPage` own the listen → detect silence → replay → relisten lifecycle; and enhance the existing local Web Audio replay graph. The existing recorder hook remains shared and its public API is unchanged.

**Tech Stack:** React 18, browser MediaRecorder and Web Audio APIs, Vitest 4, Playwright 1.61, ESLint, Vite 8.

## Global Constraints

- The only initial control is `Enable microphone / மைக்ரோஃபோனை இயக்கவும்`; there are no per-turn Start or Stop controls.
- Required silence is exactly 3,500 ms and is counted only after valid speech begins.
- Raw audio, recognized text, and child utterances never leave the page and are never stored.
- The effect is local signal processing; do not describe it as voice cloning or guaranteed gender conversion.
- Every Pippin-specific instruction, status, action, fallback, accessibility label, and privacy message displays English and Tamil together.
- Aggregate reporting continues to contain only turn count and duration.

---

## File structure

- Create `frontend/src/features/storybook/voiceTurnDetector.js`: pure voice/silence state machine and constants.
- Create `frontend/src/features/storybook/voiceTurnDetector.test.js`: deterministic detector tests with numeric timestamps.
- Modify `frontend/src/features/storybook/kittenEcho.js`: local high-shelf/compressor replay graph and stable playback constant.
- Modify `frontend/src/features/storybook/kittenEcho.test.js`: audio-graph, fallback, resource-disposal, and privacy assertions.
- Modify `frontend/src/pages/PippinPage.jsx`: bilingual copy and hands-free lifecycle.
- Modify `frontend/src/components/storybook/PippinStorybook.jsx`: bilingual SVG title and description for assistive technology.
- Modify `frontend/src/components/interactive/SensorySettingsPanel.jsx`: `bi` locale displaying paired English/Tamil setting labels.
- Modify `frontend/src/components/interactive/play.css`: non-interactive bilingual status styling and mobile layout.
- Modify `frontend/tests/character-coaches.spec.js`: controllable microphone energy mock and end-to-end lifecycle tests.
- Modify `docs/qa/tamil-storybook-verification.md`: manual Pippin permission, silence, replay, relisten, privacy, and denial checks.

### Task 1: Deterministic voice-turn detector

**Files:**
- Create: `frontend/src/features/storybook/voiceTurnDetector.js`
- Create: `frontend/src/features/storybook/voiceTurnDetector.test.js`

**Interfaces:**
- Consumes: normalized analyser levels in the inclusive range `0..1` and monotonic millisecond timestamps.
- Produces: `createVoiceTurnDetector(options)` with `sample(level, now)`, `reset(now)`, and `getState()`; each `sample` returns `{ event: 'none' | 'speech-started' | 'turn-complete' | 'max-duration', hasSpeech, speaking }`. Before speech, a bounded exponential moving average tracks room noise and sets the effective trigger to `max(0.1, min(0.24, noiseFloor + 0.045))`.

- [ ] **Step 1: Write the failing detector tests**

```js
const detector = createVoiceTurnDetector({ silenceMs: 3500, minSpeechMs: 180, maxTurnMs: 15000, threshold: 0.1 })
expect(detector.sample(0.02, 3501).event).toBe('none')
detector.sample(0.2, 4000)
detector.sample(0.2, 4200)
expect(detector.sample(0.02, 7699).event).toBe('none')
expect(detector.sample(0.02, 7700).event).toBe('turn-complete')
```

Add separate cases for a sub-180 ms spike, a steady `0.08` room noise floor followed by `0.16` speech, speech resuming during the silence window, one-shot completion, the 15,000 ms safety cap, invalid levels, and `reset()`.

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `npm test -- --run src/features/storybook/voiceTurnDetector.test.js`

Expected: FAIL because `voiceTurnDetector.js` does not exist.

- [ ] **Step 3: Implement the minimal state machine**

```js
export const PIPPIN_SILENCE_MS = 3500
export const PIPPIN_MAX_TURN_MS = 15000

export function createVoiceTurnDetector({ silenceMs = PIPPIN_SILENCE_MS, minSpeechMs = 180, maxTurnMs = PIPPIN_MAX_TURN_MS, threshold = 0.1 } = {}) {
  let state
  const reset = (now = 0) => { state = { startedAt: now, voiceStartedAt: null, lastVoiceAt: null, hasSpeech: false, announcedSpeech: false, completed: false, noiseFloor: 0.03 } }
  reset()
  const sample = (rawLevel, now) => {
    const level = Number.isFinite(rawLevel) ? Math.max(0, Math.min(1, rawLevel)) : 0
    const effectiveThreshold = Math.max(threshold, Math.min(0.24, state.noiseFloor + 0.045))
    if (state.completed) return { event: 'none', hasSpeech: state.hasSpeech, speaking: false }
    if (now - state.startedAt >= maxTurnMs) { state.completed = true; return { event: 'max-duration', hasSpeech: state.hasSpeech, speaking: false } }
    if (!state.hasSpeech && level < effectiveThreshold) state.noiseFloor = state.noiseFloor * 0.92 + level * 0.08
    if (level >= effectiveThreshold) {
      state.voiceStartedAt ??= now
      state.lastVoiceAt = now
      if (!state.hasSpeech && now - state.voiceStartedAt >= minSpeechMs) state.hasSpeech = true
      const event = state.hasSpeech && !state.announcedSpeech ? 'speech-started' : 'none'
      state.announcedSpeech ||= state.hasSpeech
      return { event, hasSpeech: state.hasSpeech, speaking: true }
    }
    state.voiceStartedAt = state.hasSpeech ? state.voiceStartedAt : null
    if (state.hasSpeech && now - state.lastVoiceAt >= silenceMs) { state.completed = true; return { event: 'turn-complete', hasSpeech: true, speaking: false } }
    return { event: 'none', hasSpeech: state.hasSpeech, speaking: false }
  }
  return { sample, reset, getState: () => ({ ...state }) }
}
```

- [ ] **Step 4: Run detector tests and confirm GREEN**

Run: `npm test -- --run src/features/storybook/voiceTurnDetector.test.js`

Expected: all detector tests PASS.

- [ ] **Step 5: Commit the detector unit**

```powershell
git add frontend/src/features/storybook/voiceTurnDetector.js frontend/src/features/storybook/voiceTurnDetector.test.js
git commit -m "feat: detect hands-free Pippin voice turns"
```

### Task 2: Bright local kitten replay

**Files:**
- Modify: `frontend/src/features/storybook/kittenEcho.js`
- Modify: `frontend/src/features/storybook/kittenEcho.test.js`

**Interfaces:**
- Consumes: the existing non-empty `Blob` accepted by `createKittenEcho().play(blob)`.
- Produces: the same `play`, `stop`, and `dispose` API; exports `KITTEN_RATE = 1.24` for stable tests.

- [ ] **Step 1: Extend the Web Audio fixture and write failing expectations**

Add `createBiquadFilter()` and `createDynamicsCompressor()` mocks. Assert the graph and tuning:

```js
expect(fixture.sources[0].playbackRate.value).toBe(1.24)
expect(fixture.filter.type).toBe('highshelf')
expect(fixture.filter.frequency.value).toBe(1800)
expect(fixture.filter.gain.value).toBe(4)
expect(fixture.connections).toEqual([
  ['source', 'highshelf'], ['highshelf', 'compressor'],
  ['compressor', 'analyser'], ['analyser', 'gain'], ['gain', 'destination'],
])
```

Also update fallback audio to expect `playbackRate === 1.24` and disposal to expect filter/compressor disconnection.

- [ ] **Step 2: Run the focused replay tests and confirm RED**

Run: `npm test -- --run src/features/storybook/kittenEcho.test.js`

Expected: FAIL at the old `1.18` rate and missing filter/compressor graph.

- [ ] **Step 3: Implement the local signal chain**

```js
export const KITTEN_RATE = 1.24
const filter = context.createBiquadFilter()
filter.type = 'highshelf'
filter.frequency.value = 1800
filter.gain.value = 4
const compressor = context.createDynamicsCompressor()
source.connect(filter)
filter.connect(compressor)
compressor.connect(analyser)
analyser.connect(gain)
gain.connect(context.destination)
```

Store both nodes in `current`, disconnect them in `finishCurrent`, and preserve the Audio-element local fallback.

- [ ] **Step 4: Run replay tests and confirm GREEN**

Run: `npm test -- --run src/features/storybook/kittenEcho.test.js`

Expected: all replay and aggregate-report tests PASS, with no fetch or XHR calls.

- [ ] **Step 5: Commit the replay unit**

```powershell
git add frontend/src/features/storybook/kittenEcho.js frontend/src/features/storybook/kittenEcho.test.js
git commit -m "feat: brighten Pippin local kitten echo"
```

### Task 3: Bilingual hands-free Pippin lifecycle

**Files:**
- Modify: `frontend/src/pages/PippinPage.jsx`
- Modify: `frontend/src/components/storybook/PippinStorybook.jsx`
- Modify: `frontend/src/components/interactive/SensorySettingsPanel.jsx`
- Modify: `frontend/src/components/interactive/play.css`
- Test: `frontend/tests/character-coaches.spec.js`

**Interfaces:**
- Consumes: `createVoiceTurnDetector`, `readAnalyserLevel`, existing `useAudioRecorder`, and `createKittenEcho`.
- Produces: phase flow `permission → listening → preparing → repeating → listening`; a single permission button before activation; no recording Start/Stop buttons.

- [ ] **Step 1: Replace the Pippin browser test with failing bilingual/hands-free assertions**

Make microphone energy controllable through `window.__mockMicLevel`, give the mock analyser `frequencyBinCount: 128` and `getByteFrequencyData(array)`, and record `window.__mediaRecorderStarts` and `window.__mediaRecorderStops`. Assert:

```js
await expect(page.getByRole('button', { name: 'Enable microphone / மைக்ரோஃபோனை இயக்கவும்' })).toBeVisible()
await expect(page.getByRole('button', { name: /Start|Stop|பேசலாம்|முடித்தேன்/i })).toHaveCount(0)
await page.getByRole('button', { name: 'Enable microphone / மைக்ரோஃபோனை இயக்கவும்' }).click()
await expect(page.getByText('Listening / கேட்கிறேன்')).toBeVisible()
await page.evaluate(() => { window.__mockMicLevel = 0.35 })
await page.waitForTimeout(250)
await page.evaluate(() => { window.__mockMicLevel = 0 })
await expect.poll(() => page.evaluate(() => window.__mediaRecorderStops), { timeout: 5000 }).toBe(1)
await expect.poll(() => page.evaluate(() => window.__kittenPlaybackRates)).toEqual([1.24])
await expect.poll(() => page.evaluate(() => window.__mediaRecorderStarts)).toBe(2)
```

Use a test-only `silenceMs={...}` only if injected through an exported Pippin lifecycle hook; otherwise keep the browser assertion at the real 3.5-second boundary and let unit tests cover exact timing.

- [ ] **Step 2: Run the focused Playwright test and confirm RED**

Run: `npx playwright test tests/character-coaches.spec.js --grep "Pippin"`

Expected: FAIL because Start/Stop controls and Tamil-only copy still exist.

- [ ] **Step 3: Implement the automatic lifecycle with cleanup guards**

Add refs for the detector, animation frame, mounted state, and activation state. The sampling loop must use this structure:

```js
const monitorTurn = () => {
  const level = readAnalyserLevel(analyserRef.current)
  setAudioLevel(level)
  const { event } = detectorRef.current.sample(level, performance.now())
  if (event === 'turn-complete' || event === 'max-duration') {
    pendingRepeatRef.current = true
    stopRecording()
    setMood('preparing')
    setMessage('Getting ready / தயாராகிறேன்')
    return
  }
  monitorFrameRef.current = requestAnimationFrame(monitorTurn)
}
```

After `echo.play(blob)` resolves, call the guarded `beginAutomaticTurn()` again. For `max-duration` with `hasSpeech === false`, stop and discard the silent turn before automatically restarting; never replay empty room noise. Do not auto-restart after permission denial, navigation, Reset, Dance, or Sing. Prevent overlapping start calls with an in-flight ref. Dispose timers, frames, stream, echo, and speech on unmount.

Use paired copy including:

```js
const COPY = {
  welcome: 'Hello! I repeat your words / வணக்கம்! நீங்கள் சொல்வதை நான் திரும்பச் சொல்வேன்',
  listening: 'Listening / கேட்கிறேன்',
  preparing: 'Getting ready / தயாராகிறேன்',
  repeating: 'Pippin repeats / பிப்பின் திரும்பச் சொல்கிறான்',
  privacy: 'Your voice stays on this device and is not saved / உங்கள் குரல் இந்தச் சாதனத்திலேயே இருக்கும்; சேமிக்கப்படாது.',
}
```

Set shell locale to `bi`, pair Dance/Sing/Reset/fallback labels, and preserve the aggregate-only report call on exit.

- [ ] **Step 4: Add bilingual sensory labels and status styling**

For `locale === 'bi'`, derive labels by matching English and Tamil options by index and joining them as `${english} / ${tamil}`. Add `.pippin-listening-status` styling with a visible pulsing dot and a reduced-motion override that disables the pulse.

- [ ] **Step 5: Run Pippin browser tests and confirm GREEN**

Run: `npx playwright test tests/character-coaches.spec.js --grep "Pippin"`

Expected: the automatic lifecycle and permission-denial tests PASS; no evaluation/upload request occurs and storage contains no child audio or transcript.

- [ ] **Step 6: Commit the experience unit**

```powershell
git add frontend/src/pages/PippinPage.jsx frontend/src/components/interactive/SensorySettingsPanel.jsx frontend/src/components/interactive/play.css frontend/tests/character-coaches.spec.js
git commit -m "feat: make Pippin bilingual and hands-free"
```

### Task 4: Regression, quality, and live verification

**Files:**
- Modify: `docs/qa/tamil-storybook-verification.md`

**Interfaces:**
- Consumes: completed detector, replay, and Pippin lifecycle.
- Produces: a reproducible QA record and a running frontend reachable at `http://127.0.0.1:5173`.

- [ ] **Step 1: Run focused unit tests**

Run: `npm test -- --run src/features/storybook/voiceTurnDetector.test.js src/features/storybook/kittenEcho.test.js`

Expected: PASS.

- [ ] **Step 2: Run the entire frontend unit suite**

Run: `npm test`

Expected: all tests PASS.

- [ ] **Step 3: Run static checks and production build**

Run: `npm run lint`

Expected: zero warnings and zero errors.

Run: `npm run build`

Expected: Vite build succeeds.

- [ ] **Step 4: Run the complete Playwright suite**

Run: `npx playwright test`

Expected: all registration, Kavi, Pippin, mobile, and privacy tests PASS.

- [ ] **Step 5: Perform live smoke checks**

Verify `http://127.0.0.1:5173/play/pippin` loads, microphone permission appears once, speech plus 3.5 seconds of silence produces one replay, a second listening turn begins automatically, Dance/Sing suspend listening, denial shows bilingual fallbacks, and a 390×844 viewport has no horizontal overflow.

- [ ] **Step 6: Update QA evidence**

Record the exact unit, lint, build, and browser commands and counts in `docs/qa/tamil-storybook-verification.md`. Include the privacy result: no request body or web storage field contains audio, blob, transcript, utterance, or the mock child phrase.

- [ ] **Step 7: Commit verification evidence**

```powershell
git add docs/qa/tamil-storybook-verification.md
git commit -m "docs: verify bilingual hands-free Pippin"
```

## Self-review

- Spec coverage: permission activation, bilingual copy, speech-gated silence, 3.5-second completion, maximum duration, replay, automatic relisten, local privacy, aggregate reporting, fallback, cleanup, accessibility, reduced motion, and full verification each map to a task above.
- Placeholder scan: every implementation and test step names concrete behavior and commands; no unresolved markers remain.
- Type consistency: Tasks 1 and 3 consistently use `createVoiceTurnDetector().sample(level, now)` and the four event names; Tasks 2 and 3 keep `createKittenEcho().play(blob)` unchanged; `useAudioRecorder` remains unchanged.
