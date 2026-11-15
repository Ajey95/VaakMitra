# Play & Practice Four-Game Animation Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add rich, state-driven animation, Tamil guidance, responsive production art, and sensory-safe rewards to Breath Balloon, River Rescue, Mouth Mirror, and Talk Together without changing Play with Pippin.

**Architecture:** Keep the existing reducers, media adapters, reporting calls, and session shell as the source of truth. Add a pure presentation-state module and reusable decorative effect layer, then connect each current game state to named visual states and game-specific CSS. Use generated raster art only for central scene imagery; keep controls, text, accessibility states, and therapy feedback code-native.

**Tech Stack:** React 18, Vite 8, Vitest 4, Playwright 1.61, CSS animations, existing Zustand interaction preferences, OpenAI Image Gen for raster scene assets.

## Global Constraints

- Scope is limited to Breath Balloon, River Rescue, Mouth Mirror, and Talk Together.
- Do not modify `frontend/src/pages/PippinPage.jsx`, Pippin components, Pippin features, Pippin tests, or Pippin assets.
- Preserve existing microphone, camera, speech-evaluation, reporting, and privacy behavior.
- Do not add backend schema or API changes, new ML models, a game engine, a canvas rewrite, or a new runtime animation dependency.
- Tamil is the primary child-facing guidance language; visible and spoken instructions must convey the same state.
- Camera frames, raw audio, and unrestricted transcripts must never be stored.
- Every animation must obey saved `motionLevel`, saved `celebrationLevel`, calm mode, and `prefers-reduced-motion`.
- Decorative motion must not obscure controls, instructions, the camera feed, or the therapy target.
- Prefer transform and opacity animations; do not drive decorative motion with per-frame React state.
- Maintain at least 44 × 44 CSS-pixel primary touch targets and prevent mobile horizontal overflow.
- Preserve the current working tree. Never reset, discard, or overwrite existing uncommitted work.
- Do not commit implementation files that already contain user-owned uncommitted changes; stage and commit only isolated new files when doing so cannot capture unrelated work.

---

### Task 1: Pure presentation state and Tamil copy

**Files:**
- Create: `frontend/src/features/interactive/animationPresentation.js`
- Create: `frontend/src/features/interactive/animationPresentation.test.js`

**Interfaces:**
- Consumes: `{ mode, level, target }`, `{ motionLevel, celebrationLevel }`, and Talk Together assistance values.
- Produces: `getBreathVisualState`, `getEffectProfile`, `getTamilPrompt`, `TALK_TOGETHER_SCENES`, and `getTalkTogetherReward`.

- [ ] **Step 1: Write the failing presentation-state tests**

```js
import { describe, expect, it } from 'vitest'
import {
  TALK_TOGETHER_SCENES,
  getBreathVisualState,
  getEffectProfile,
  getTamilPrompt,
  getTalkTogetherReward,
} from './animationPresentation'

describe('interactive animation presentation', () => {
  it('classifies balloon input without rewarding excessive volume', () => {
    const target = [0.25, 0.7]
    expect(getBreathVisualState({ mode: 'playing', level: 0.1, target })).toBe('too-weak')
    expect(getBreathVisualState({ mode: 'playing', level: 0.45, target })).toBe('steady')
    expect(getBreathVisualState({ mode: 'playing', level: 0.9, target })).toBe('too-strong')
    expect(getBreathVisualState({ mode: 'success', level: 0.45, target })).toBe('success')
    expect(getBreathVisualState({ mode: 'complete', level: 0, target })).toBe('complete')
  })

  it('turns sensory preferences into bounded effect profiles', () => {
    expect(getEffectProfile({ motionLevel: 'full', celebrationLevel: 'full' })).toEqual({ ambient: true, particles: 18, travel: true, durationMs: 4000 })
    expect(getEffectProfile({ motionLevel: 'reduced', celebrationLevel: 'gentle' })).toEqual({ ambient: true, particles: 6, travel: false, durationMs: 1800 })
    expect(getEffectProfile({ motionLevel: 'minimal', celebrationLevel: 'none' })).toEqual({ ambient: false, particles: 0, travel: false, durationMs: 0 })
  })

  it('provides Tamil guidance for every required balloon state', () => {
    for (const state of ['intro', 'too-weak', 'steady', 'too-strong', 'stopped', 'success', 'complete']) {
      expect(getTamilPrompt('breath-balloon', state)).toMatch(/[\u0B80-\u0BFF]/)
    }
  })

  it('maps five Talk Together missions and supportive reward levels', () => {
    expect(TALK_TOGETHER_SCENES.map(({ id }) => id)).toEqual(['ask-water', 'choose-snack', 'name-object', 'imitate-turns', 'say-thanks'])
    expect(getTalkTogetherReward('independent').intensity).toBe('full')
    expect(getTalkTogetherReward('modelled').intensity).toBe('gentle')
    expect(getTalkTogetherReward('skipped').intensity).toBe('none')
  })
})
```

- [ ] **Step 2: Run the focused test and observe the missing-module failure**

Run: `npm test -- --run src/features/interactive/animationPresentation.test.js`

Expected: FAIL because `animationPresentation.js` does not exist.

- [ ] **Step 3: Implement deterministic presentation helpers**

```js
const TAMIL_PROMPTS = Object.freeze({
  'breath-balloon': Object.freeze({
    intro: 'வணக்கம்! இன்று நம்ம பலூனை வானத்தில் பறக்க விடலாமா?',
    'too-weak': 'சிறிது பலமாக முயற்சி செய்வோம்.',
    steady: 'அப்படியே மெதுவாக ஊதுங்கள்!',
    'too-strong': 'மிக வேகமாக இல்லை… மெதுவாக ஊதுங்கள்.',
    stopped: 'பரவாயில்லை! இன்னும் கொஞ்சம் மெதுவாக ஊதலாம்.',
    success: 'அருமை! பலூன் மேலே பறக்கிறது!',
    complete: 'அருமை! நீங்க ரொம்ப நல்லா செய்தீங்க!',
  }),
  'river-rescue': Object.freeze({
    intro: 'எனக்கு வீட்டிற்குச் செல்ல உதவுவாயா?',
    retry: 'பரவாயில்லை… இன்னொரு முறை முயற்சி செய்வோம்.',
    success: 'அருமை! கவி அடுத்த படிக்குச் செல்கிறான்!',
    complete: 'அருமை! கவி பாதுகாப்பாகக் கடந்துவிட்டான்!',
  }),
  'mouth-mirror': Object.freeze({ matched: 'சரியாக செய்தாய்!', retry: 'மீண்டும் மெதுவாக முயற்சி செய்வோம்.' }),
  'talk-together': Object.freeze({ independent: 'சிறப்பாக பேசினாய்!', prompted: 'மிகவும் அருமை!', complete: 'நீங்கள் தினமும் இன்னும் சிறப்பாக முன்னேறுகிறீர்கள்!' }),
})

export function getBreathVisualState({ mode, level, target = [0.25, 0.7] }) {
  if (['success', 'support', 'complete'].includes(mode)) return mode === 'support' ? 'stopped' : mode
  if (mode !== 'playing') return mode === 'intro' ? 'intro' : 'idle'
  if (level < target[0]) return 'too-weak'
  if (level > target[1]) return 'too-strong'
  return 'steady'
}

export function getEffectProfile({ motionLevel = 'full', celebrationLevel = 'gentle' } = {}) {
  if (motionLevel === 'minimal' || celebrationLevel === 'none') return { ambient: false, particles: 0, travel: false, durationMs: 0 }
  if (motionLevel === 'reduced' || celebrationLevel === 'gentle') return { ambient: true, particles: 6, travel: false, durationMs: 1800 }
  return { ambient: true, particles: 18, travel: true, durationMs: 4000 }
}

export function getTamilPrompt(game, state) {
  return TAMIL_PROMPTS[game]?.[state] || ''
}

export const TALK_TOGETHER_SCENES = Object.freeze([
  { id: 'ask-water', environment: 'kitchen', title: 'தண்ணீர் கேட்போம்' },
  { id: 'choose-snack', environment: 'grocery', title: 'சிற்றுண்டி தேர்வு' },
  { id: 'name-object', environment: 'classroom', title: 'பொருளைக் கண்டுபிடிப்போம்' },
  { id: 'imitate-turns', environment: 'park', title: 'மாறி மாறிச் செய்வோம்' },
  { id: 'say-thanks', environment: 'birthday', title: 'நன்றி சொல்வோம்' },
])

export function getTalkTogetherReward(assistance) {
  if (assistance === 'independent') return { intensity: 'full', promptKey: 'independent' }
  if (assistance === 'skipped') return { intensity: 'none', promptKey: '' }
  return { intensity: 'gentle', promptKey: 'prompted' }
}
```

- [ ] **Step 4: Run the focused test**

Run: `npm test -- --run src/features/interactive/animationPresentation.test.js`

Expected: PASS.

- [ ] **Step 5: Check the new files without staging existing work**

Run: `git diff --check -- frontend/src/features/interactive/animationPresentation.js frontend/src/features/interactive/animationPresentation.test.js`

Expected: no output.

---

### Task 2: Production art and reusable scene effects

**Files:**
- Create: `frontend/public/assets/interactive/breath-balloon/breath-balloon-meadow.png`
- Create: `frontend/public/assets/interactive/mouth-mirror/mouth-mirror-therapist.png`
- Create: `frontend/public/assets/interactive/talk-together/talk-together-environments.png`
- Create: `frontend/src/components/interactive/SceneEffects.jsx`
- Create: `frontend/src/components/interactive/SceneEffects.test.jsx`
- Create: `frontend/src/components/interactive/scene-effects.css`
- Create: `frontend/src/features/interactive/sceneAudio.js`
- Create: `frontend/src/features/interactive/sceneAudio.test.js`

**Interfaces:**
- Consumes: `variant`, `state`, `effectProfile`, and `label` props.
- Produces: `AmbientEffects`, `CelebrationLayer`, and `TamilStatus` components with stable `data-*` hooks, plus `createSceneAudioController(scope)` for Tamil speech and short synchronized tones.

- [ ] **Step 1: Generate the three central raster assets**

Use Image Gen with these exact art briefs:

```text
Breath Balloon: 16:9 Tamil children's storybook meadow background, blue sky, soft clouds, smiling sun, distant birds, butterflies, colorful flowers and grass, open clear center and lower-center area for a code-native balloon, no balloon, no text, no logos, warm 2D gouache illustration, polished educational game art, layered depth, calm bright palette.

Mouth Mirror therapist: friendly South Indian woman speech therapist character, waist-up, warm smile, one hand encouraging, child-safe 2D storybook illustration, lavender and gold clothing, clean transparent background, no text, no logos, centered with generous transparent padding.

Talk Together: one wide five-panel seamless environment strip with equal panels showing a cozy home kitchen, cheerful grocery shop, colorful classroom, sunny park, and birthday room; consistent Tamil children's storybook art direction, open center foreground in every panel for code-native characters and prompts, no text, no logos, clear boundaries between panels.
```

Save the returned files at the exact asset paths above and visually inspect each with `view_image`.

- [ ] **Step 2: Write the failing shared-effects render test**

```jsx
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { AmbientEffects, CelebrationLayer, TamilStatus } from './SceneEffects'

describe('SceneEffects', () => {
  it('keeps decorative effects hidden from assistive technology', () => {
    const html = renderToStaticMarkup(<AmbientEffects variant="meadow" enabled />)
    expect(html).toContain('aria-hidden="true"')
    expect(html).toContain('data-variant="meadow"')
  })

  it('renders the bounded number of configured particles', () => {
    const html = renderToStaticMarkup(<CelebrationLayer variant="stars" state="success" effectProfile={{ particles: 6, travel: false, durationMs: 1800 }} />)
    expect((html.match(/scene-particle/g) || []).length).toBe(6)
    expect(html).toContain('data-travel="false"')
  })

  it('announces Tamil status politely', () => {
    const html = renderToStaticMarkup(<TamilStatus label="சரியாக செய்தாய்!" />)
    expect(html).toContain('aria-live="polite"')
    expect(html).toContain('சரியாக செய்தாய்!')
  })
})
```

- [ ] **Step 3: Run the test and observe the missing-component failure**

Run: `npm test -- --run src/components/interactive/SceneEffects.test.jsx`

Expected: FAIL because `SceneEffects.jsx` does not exist.

- [ ] **Step 4: Implement reusable semantic effects**

```jsx
import './scene-effects.css'

export function AmbientEffects({ variant, enabled = true }) {
  if (!enabled) return null
  return <div className="scene-ambient" data-variant={variant} aria-hidden="true"><i /><i /><i /><i /><i /><i /></div>
}

export function CelebrationLayer({ variant, state, effectProfile }) {
  const count = Math.max(0, Math.min(24, effectProfile?.particles || 0))
  if (!count) return null
  return (
    <div className="scene-celebration" data-variant={variant} data-state={state} data-travel={String(Boolean(effectProfile?.travel))} style={{ '--effect-duration': `${effectProfile.durationMs}ms` }} aria-hidden="true">
      {Array.from({ length: count }, (_, index) => <i className="scene-particle" key={index} style={{ '--particle-index': index }} />)}
    </div>
  )
}

export function TamilStatus({ label }) {
  return <span className="scene-status" role="status" aria-live="polite">{label}</span>
}
```

Create `scene-effects.css` with fixed non-interactive layers, transform/opacity keyframes, deterministic particle placement from `--particle-index`, `prefers-reduced-motion` overrides, and `html[data-interaction-motion="minimal"]` rules that disable all decorative animation.

- [ ] **Step 5: Run the component test and production build**

First write `sceneAudio.test.js` with deterministic browser mocks:

```js
import { describe, expect, it, vi } from 'vitest'
import { createSceneAudioController } from './sceneAudio'

function fixture() {
  const spoken = []
  class Utterance { constructor(text) { this.text = text; this.lang = '' } }
  const oscillator = { connect: vi.fn(), start: vi.fn(), stop: vi.fn(), frequency: { value: 0 } }
  const gain = { connect: vi.fn(), gain: { setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() } }
  const context = { currentTime: 1, destination: {}, createOscillator: () => oscillator, createGain: () => gain, close: vi.fn() }
  const scope = {
    SpeechSynthesisUtterance: Utterance,
    speechSynthesis: { cancel: vi.fn(), speak: (utterance) => spoken.push(utterance) },
    AudioContext: class { constructor() { return context } },
  }
  return { scope, spoken, oscillator, context }
}

describe('scene audio controller', () => {
  it('speaks Tamil only when enabled and activated', () => {
    const { scope, spoken } = fixture()
    const audio = createSceneAudioController(scope)
    expect(audio.speakTamil('அருமை!', { enabled: true, activated: false })).toBe(false)
    expect(audio.speakTamil('அருமை!', { enabled: true, activated: true })).toBe(true)
    expect(spoken[0]).toMatchObject({ text: 'அருமை!', lang: 'ta-IN' })
  })

  it('plays bounded success tones and cleans up', () => {
    const { scope, oscillator, context } = fixture()
    const audio = createSceneAudioController(scope)
    expect(audio.playEffect('success', { enabled: true, activated: true })).toBe(true)
    expect(oscillator.start).toHaveBeenCalledOnce()
    expect(oscillator.stop).toHaveBeenCalledOnce()
    audio.stop()
    expect(context.close).toHaveBeenCalledOnce()
  })
})
```

Run: `npm test -- --run src/features/interactive/sceneAudio.test.js`

Expected: FAIL because `sceneAudio.js` does not exist.

Implement `createSceneAudioController(scope)` so `speakTamil(text, { enabled, activated })` cancels prior speech, creates a `SpeechSynthesisUtterance`, assigns `lang = 'ta-IN'`, and speaks only after activation. Implement `playEffect(name, { enabled, activated })` with a short Web Audio oscillator envelope for `success`, `sparkle`, `water`, and `sticker`; return `false` without throwing when disabled or unsupported. Implement `stop()` to cancel speech and close the owned audio context.

Pages call `speakTamil` only after their existing start/listen/camera/model/confirm gestures and call `playEffect` only when a corresponding visual reaction begins. Pause, calm mode, sound disable, route exit, and component cleanup call `stop()`.

- [ ] **Step 6: Run shared tests and the production build**

Run: `npm test -- --run src/components/interactive/SceneEffects.test.jsx src/features/interactive/sceneAudio.test.js`, then run `npm run build`.

Expected: PASS and successful Vite build.

---

### Task 3: Breath Balloon state-driven scene

**Files:**
- Modify: `frontend/src/components/interactive/BalloonScene.jsx`
- Create: `frontend/src/components/interactive/BalloonScene.test.jsx`
- Modify: `frontend/src/pages/BreathBalloonPage.jsx`
- Modify: `frontend/src/components/interactive/play.css`

**Interfaces:**
- Consumes: Task 1 `getBreathVisualState`, `getEffectProfile`, `getTamilPrompt`; Task 2 `AmbientEffects`, `CelebrationLayer`, `TamilStatus`.
- Produces: `BalloonScene` markup with `data-visual-state` and the existing level, target, score, obstacle, and letter-announcement behavior.

- [ ] **Step 1: Write a failing static-render test for balloon expressions**

```jsx
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import BalloonScene from './BalloonScene'

describe('BalloonScene', () => {
  it('renders the requested expression and preserves its accessible meter', () => {
    const html = renderToStaticMarkup(<BalloonScene level={0.9} target={[0.25, 0.7]} active visualState="too-strong" motionLevel="full" />)
    expect(html).toContain('data-visual-state="too-strong"')
    expect(html).toContain('balloon-face')
    expect(html).toContain('Voice level 90 percent')
  })

  it('renders the flight reward only for completion', () => {
    expect(renderToStaticMarkup(<BalloonScene level={0} visualState="complete" motionLevel="full" />)).toContain('balloon-flight-reward')
    expect(renderToStaticMarkup(<BalloonScene level={0} visualState="idle" motionLevel="full" />)).not.toContain('balloon-flight-reward')
  })
})
```

- [ ] **Step 2: Run the focused test and observe the missing-state failure**

Run: `npm test -- --run src/components/interactive/BalloonScene.test.jsx`

Expected: FAIL because the current component has no `data-visual-state`, face, or flight reward.

- [ ] **Step 3: Add semantic scene markup without changing input mechanics**

Add these props and hooks to `BalloonScene`:

```jsx
export default function BalloonScene({ visualState = 'idle', motionLevel = 'full', effectProfile, ...existingProps }) {
  // Keep all existing level, target, obstacle, score, and meter calculations.
  return (
    <div className="balloon-scene" data-visual-state={visualState} data-motion={motionLevel}>
      <div className="balloon-scene__sky" style={{ backgroundImage: "url('/assets/interactive/breath-balloon/breath-balloon-meadow.png')" }}>
        <AmbientEffects variant="meadow" enabled={effectProfile?.ambient} />
        {/* existing letter path */}
        <div className="balloon-scene__balloon">
          <span className="balloon-scene__shine" />
          <span className="balloon-face" aria-hidden="true"><i className="balloon-eye" /><i className="balloon-eye" /><i className="balloon-mouth" /></span>
          <span className="balloon-arm balloon-arm--left" /><span className="balloon-arm balloon-arm--right" />
          <span className="balloon-scene__knot" /><span className="balloon-scene__string" />
        </div>
        {visualState === 'complete' ? <div className="balloon-flight-reward" aria-hidden="true"><i className="balloon-rainbow" /><i className="balloon-treasure" /></div> : null}
        <CelebrationLayer variant="stars" state={visualState} effectProfile={effectProfile} />
      </div>
      {/* existing announcement, meter, and score */}
    </div>
  )
}
```

- [ ] **Step 4: Connect page state, preferences, and Tamil visible guidance**

In `BreathBalloonPage.jsx`, derive rather than store presentation state:

```js
const visualState = getBreathVisualState({ mode, level, target: step.target })
const effectProfile = getEffectProfile(preferences)
const tamilPrompt = getTamilPrompt('breath-balloon', visualState)
```

Pass these values to `BalloonScene`, render `<TamilStatus label={tamilPrompt} />`, and replace the intro/success/completion child-facing titles with the matching Tamil prompt while retaining short English details and all existing buttons, privacy copy, calibration, score submission, and fallbacks.

Create one scene-audio controller in a ref. Mark it activated from the existing microphone or screen-control start gesture, speak only when `tamilPrompt` changes after activation, play `success` at round success and `sparkle` at completion, and stop it on pause, sound disable, restart, exit, and unmount.

- [ ] **Step 5: Implement game-specific CSS states**

Add bounded keyframes and selectors for `[data-visual-state="too-weak"]`, `steady`, `too-strong`, `stopped`, `success`, and `complete`. Include blinking eyes, mouth changes, a single surprised spin, arm wave, steady-zone glow, wind/flower response, rainbow, treasure, and mobile/reduced-motion rules. Do not animate layout properties.

- [ ] **Step 6: Run focused and existing Breath Balloon tests**

Run: `npm test -- --run src/components/interactive/BalloonScene.test.jsx src/features/interactive/animationPresentation.test.js src/features/arcade/breathBalloonActivity.test.js src/features/interactive/audioLevel.test.js`

Expected: PASS.

---

### Task 4: River Rescue living storybook reactions

**Files:**
- Modify: `frontend/src/components/storybook/KaviStorybookScene.jsx`
- Create: `frontend/src/components/storybook/KaviStorybookScene.test.jsx`
- Modify: `frontend/src/pages/RiverRescuePage.jsx`
- Modify: `frontend/src/components/interactive/play.css`

**Interfaces:**
- Consumes: current Kavi five-page images and reducer phases; Task 1 `getEffectProfile` and `getTamilPrompt`; Task 2 shared effects.
- Produces: Kavi scene markup with `data-mood`, `data-page`, `data-motion`, animated river/lotus/stone overlays, and bounded success/retry/completion reactions.

- [ ] **Step 1: Write the failing Kavi scene test**

```jsx
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import KaviStorybookScene from './KaviStorybookScene'

describe('KaviStorybookScene', () => {
  it('renders supportive river overlays for the current mood', () => {
    const html = renderToStaticMarkup(<KaviStorybookScene pageIndex={2} mood="encourage" motionLevel="full" picture="/level.png" message="மீண்டும் முயற்சி செய்வோம்" />)
    expect(html).toContain('data-mood="encourage"')
    expect(html).toContain('kavi-river-effects')
    expect(html).toContain('kavi-retry-cue')
  })

  it('renders a completion celebration only for celebrate mood', () => {
    expect(renderToStaticMarkup(<KaviStorybookScene mood="celebrate" picture="/level.png" />)).toContain('kavi-crossing-celebration')
    expect(renderToStaticMarkup(<KaviStorybookScene mood="idle" picture="/level.png" />)).not.toContain('kavi-crossing-celebration')
  })
})
```

- [ ] **Step 2: Run the test and observe the missing-overlay failure**

Run: `npm test -- --run src/components/storybook/KaviStorybookScene.test.jsx`

Expected: FAIL because the overlay classes do not exist.

- [ ] **Step 3: Add overlays around the existing production artwork**

Inside the existing `<figure>`, preserve the current `<img>` and accessible caption, then add:

```jsx
<div className="kavi-river-effects" aria-hidden="true"><i className="kavi-water-glint" /><i className="kavi-lotus" /><i className="kavi-stone" /><i className="kavi-dragonfly" /></div>
{mood === 'encourage' ? <div className="kavi-retry-cue" aria-hidden="true"><i /><i /></div> : null}
{mood === 'celebrate' ? <div className="kavi-crossing-celebration" aria-hidden="true"><i className="kavi-rainbow" /></div> : null}
<AmbientEffects variant="river" enabled={effectProfile?.ambient} />
<CelebrationLayer variant="river-stars" state={mood} effectProfile={effectProfile} />
```

Add `effectProfile` as an optional prop and preserve all existing picture, page, mood, audio, walking, and motion behavior.

- [ ] **Step 4: Connect the page without replacing the current story flow**

In `RiverRescuePage.jsx`, pass `getEffectProfile(preferences)` to `KaviStorybookScene`, use the approved intro/retry/success/completion Tamil prompts as visible status supplements, and preserve the current `KAVI_STORY_PAGES`, narrator, evaluator, five-page progress, walking timer, reporting, and reset behavior.

Retain the current Tamil narrator as the spoken source of truth. Use the shared scene-audio controller only for a soft `water` effect when a success reaction starts and a `sparkle` effect at completion; stop it beside the existing narrator and recorder cleanup.

- [ ] **Step 5: Add river-specific CSS reactions**

Implement water glints, lotus bloom, stone rise, dragonfly hover, retry head-tilt cue, walking parallax, and completion rainbow/star rules. Keep ordinary reactions within 1.2 seconds, let completion run no longer than 4 seconds, and add minimal/reduced-motion overrides.

- [ ] **Step 6: Run Kavi and River regression tests**

Run: `npm test -- --run src/components/storybook/KaviStorybookScene.test.jsx src/features/storybook/kaviStory.test.js src/features/quest/riverRescueActivity.test.js`

Expected: PASS.

---

### Task 5: Magical Mouth Mirror feedback

**Files:**
- Modify: `frontend/src/components/interactive/MouthGuideOverlay.jsx`
- Create: `frontend/src/components/interactive/MouthGuideOverlay.test.jsx`
- Modify: `frontend/src/pages/MouthMirrorPage.jsx`
- Modify: `frontend/src/components/interactive/play.css`

**Interfaces:**
- Consumes: current target model, match result, hold progress, camera/model modes, Task 1 effect profile and Tamil prompts, Task 2 therapist asset and shared effects.
- Produces: `MouthGuideOverlay` with `visualState`, therapist art, slow model cue, green match outline, and camera-safe decorative framing.

- [ ] **Step 1: Write the failing Mouth Guide test**

```jsx
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import MouthGuideOverlay from './MouthGuideOverlay'

const target = { model: 'open', sound: 'அ', cue: 'வாயைத் திறக்கவும்' }

describe('MouthGuideOverlay', () => {
  it('renders the therapist and semantic feedback state', () => {
    const html = renderToStaticMarkup(<MouthGuideOverlay target={target} visualState="close" progress={0.5} />)
    expect(html).toContain('data-visual-state="close"')
    expect(html).toContain('/assets/interactive/mouth-mirror/mouth-mirror-therapist.png')
    expect(html).toContain('Hold progress 50 percent')
  })

  it('announces matched feedback in Tamil', () => {
    const html = renderToStaticMarkup(<MouthGuideOverlay target={target} visualState="matched" matched progress={1} />)
    expect(html).toContain('சரியாக செய்தாய்!')
    expect(html).toContain('is-matched')
  })
})
```

- [ ] **Step 2: Run the test and observe the missing-state failure**

Run: `npm test -- --run src/components/interactive/MouthGuideOverlay.test.jsx`

Expected: FAIL because the current overlay has no therapist asset or `visualState` hook.

- [ ] **Step 3: Implement the magical guide structure**

Add `visualState = 'model'` and `motionLevel = 'full'` props. Preserve the current face model and hold meter, add the therapist image with meaningful alt text, add gold mirror highlights outside the model face, set `data-visual-state`, and use `சரியாக செய்தாய்!` when matched. The therapist art must remain outside the camera/video grid on narrow screens.

- [ ] **Step 4: Derive page feedback state**

In `MouthMirrorPage.jsx`, derive:

```js
const mirrorVisualState = mode === 'success'
  ? 'matched'
  : mode === 'camera' && faceData.faceDetected && match.progress > 0
    ? 'close'
    : mode === 'camera' && faceData.faceDetected
      ? 'retry'
      : mode === 'model'
        ? 'model'
        : 'waiting'
```

Pass the derived state and motion preference to the overlay. Add shared celebration effects only for `matched` and `complete`. Preserve camera permission, model-only practice, geometry classification, 600 ms hold, reporting, cleanup, and the no-frame-storage statement.

Activate the shared audio controller from the camera/model selection gesture, speak the matched Tamil prompt and play `sparkle` when a hold completes, and stop all owned audio on sound disable, route exit, or unmount.

- [ ] **Step 5: Add mirror-specific CSS**

Add gold frame highlights, slow model mouth motion, amber close outline, green matched outline, therapist nod/clap, five-star completion row, responsive stacking, and reduced/minimal-motion variants. Keep all decoration outside the video’s central lip/jaw area.

- [ ] **Step 6: Run Mouth Mirror tests**

Run: `npm test -- --run src/components/interactive/MouthGuideOverlay.test.jsx src/features/mouthMirror/mouthGeometry.test.js`

Expected: PASS.

---

### Task 6: Talk Together contextual missions and rewards

**Files:**
- Modify: `frontend/src/features/together/talkTogetherActivity.js`
- Modify: `frontend/src/features/together/talkTogetherActivity.test.js`
- Modify: `frontend/src/pages/TalkTogetherPage.jsx`
- Modify: `frontend/src/components/interactive/play.css`

**Interfaces:**
- Consumes: Task 1 mission scenes, reward mappings, effect profiles, and Tamil prompts; Task 2 environment strip and shared effects.
- Produces: five contextual mission definitions with `environment`, `environmentIndex`, and Tamil `celebrateTa`, plus assistance-aware page celebration state.

- [ ] **Step 1: Extend the existing mission test and observe failure**

Add this test:

```js
it('maps the five approved missions to distinct environments and Tamil praise', () => {
  expect(TALK_TOGETHER_MISSIONS.map(({ id, environment }) => [id, environment])).toEqual([
    ['ask-water', 'kitchen'],
    ['choose-snack', 'grocery'],
    ['name-object', 'classroom'],
    ['imitate-turns', 'park'],
    ['say-thanks', 'birthday'],
  ])
  for (const mission of TALK_TOGETHER_MISSIONS) expect(mission.celebrateTa).toMatch(/[\u0B80-\u0BFF]/)
})
```

Run: `npm test -- --run src/features/together/talkTogetherActivity.test.js`

Expected: FAIL because the current mission IDs and environment fields differ.

- [ ] **Step 2: Update only mission content while preserving reporting interfaces**

Replace `TALK_TOGETHER_MISSIONS` with five objects using these exact stable IDs and environments:

```js
[
  { id: 'ask-water', environment: 'kitchen', environmentIndex: 0, title: 'Water Request', childPrompt: 'Show or tell me that you want water.', caregiverCue: 'Pause with a cup in view and wait for any word, sound, picture, or gesture.', celebrate: 'You asked for what you needed!', celebrateTa: 'சிறப்பாக கேட்டாய்!', icon: '💧' },
  { id: 'choose-snack', environment: 'grocery', environmentIndex: 1, title: 'Snack Choice', childPrompt: 'Choose between the two snacks.', caregiverCue: 'Offer two familiar pretend snacks and wait without rushing.', celebrate: 'You made a choice!', celebrateTa: 'அருமையான தேர்வு!', icon: '🍎' },
  { id: 'name-object', environment: 'classroom', environmentIndex: 2, title: 'Find and Name', childPrompt: 'Find one familiar object and show or name it.', caregiverCue: 'Point to two nearby objects and let the child choose one.', celebrate: 'You found it!', celebrateTa: 'நன்றாக கண்டுபிடித்தாய்!', icon: '⭐' },
  { id: 'imitate-turns', environment: 'park', environmentIndex: 3, title: 'Copy My Turn', childPrompt: 'Copy me, then let me copy you.', caregiverCue: 'Model one simple sound, gesture, or word, then swap roles.', celebrate: 'You shared two turns!', celebrateTa: 'மாறி மாறி அருமையாக செய்தாய்!', icon: '👏' },
  { id: 'say-thanks', environment: 'birthday', environmentIndex: 4, title: 'Kind Thank You', childPrompt: 'Say, show, or choose thank you.', caregiverCue: 'Offer a pretend gift and wait for any thank-you response.', celebrate: 'You used a kind message!', celebrateTa: 'மிகவும் அருமை!', icon: '🎁' },
]
```

Do not change `ASSISTANCE_LEVELS`, `advanceMission`, `summarizeAssistance`, `buildTalkTogetherReport`, or their aggregate-only behavior.

- [ ] **Step 3: Connect environment and assistance-aware celebration UI**

In `TalkTogetherPage.jsx`, keep the caregiver panel and confirmation flow, store the most recently confirmed assistance level, derive `reward = getTalkTogetherReward(lastAssistance)`, and render:

```jsx
<div className="together-environment" data-environment={mission.environment} style={{ '--environment-index': mission.environmentIndex }} aria-hidden="true">
  <img src="/assets/interactive/talk-together/talk-together-environments.png" alt="" />
  <span className="together-character together-character--child" />
  <span className="together-character together-character--caregiver" />
  <span className="together-turn-glow" />
</div>
```

Show `mission.celebrateTa` in the celebration view, use full/gentle/none effects based on assistance, keep skipped transitions calm, and combine five mission stickers in the completion view. Preserve caregiver assistance as the reporting source of truth.

Activate the shared audio controller from the caregiver confirmation gesture. Speak `mission.celebrateTa` and play `sticker` for non-skipped turns when sound and spoken prompts permit; skipped turns remain silent. Stop the controller on pause, sound disable, route exit, and unmount.

- [ ] **Step 4: Add environment-strip and character CSS**

Crop the five-panel strip using a 500%-wide image translated by `calc(var(--environment-index) * -20%)`. Add blinking, nodding, waving, pointing, turn glow, sticker placement, applause, balloons, mobile cropping, and reduced/minimal-motion rules. Do not place decorative content over the caregiver controls.

- [ ] **Step 5: Run Talk Together tests**

Run: `npm test -- --run src/features/together/talkTogetherActivity.test.js src/features/interactive/animationPresentation.test.js`

Expected: PASS.

---

### Task 7: Browser journeys, visual QA, and regression verification

**Files:**
- Modify: `frontend/tests/interactive-accessibility.spec.js`
- Create: `docs/qa/play-practice-animation-fidelity-ledger.md`
- Create: `docs/qa/play-practice-animation-desktop.png`
- Create: `docs/qa/play-practice-animation-mobile.png`

**Interfaces:**
- Consumes: all four upgraded games and their stable `data-*` visual hooks.
- Produces: automated browser evidence plus a written fidelity ledger covering the approved specification.

- [ ] **Step 1: Add failing browser assertions for all four scenes**

Add a browser test that:

```js
test('four upgraded games expose their animated scene states without changing Pippin', async ({ page }) => {
  await page.goto('/play/arcade/breath-balloon')
  await expect(page.locator('.breath-card')).toBeVisible()

  await page.goto('/play/quest/river-rescue')
  await expect(page.locator('[data-testid="kavi-picture-scene"]')).toHaveAttribute('data-mood', 'idle')
  await expect(page.locator('.kavi-river-effects')).toBeVisible()

  await page.goto('/play/mouth-mirror')
  await page.getByRole('button', { name: 'Model only' }).click()
  await expect(page.locator('.mouth-guide')).toHaveAttribute('data-visual-state', 'model')

  await page.goto('/play/together')
  await expect(page.locator('.together-environment')).toHaveAttribute('data-environment', 'kitchen')

  await page.goto('/play/pippin')
  await expect(page.getByRole('heading', { name: /Talk with Pippin/ })).toBeVisible()
})
```

Run: `npx playwright test tests/interactive-accessibility.spec.js --grep "four upgraded games"`

Expected: FAIL until all stable hooks are connected.

- [ ] **Step 2: Run the full frontend quality suite**

Run:

```powershell
npm test
npm run lint
npm run build
npx playwright test tests/interactive-accessibility.spec.js
```

Expected: all commands pass. If a pre-existing unrelated failure appears, capture the exact command, test name, and failure without changing unrelated files.

- [ ] **Step 3: Verify desktop and mobile core flows in a real browser**

At 1440 × 1000 and 390 × 844:

1. Open each of the four games.
2. Exercise one active, retry/fallback, success, and completion path where deterministic mocks permit.
3. Toggle calm mode and confirm decorative travel stops.
4. Confirm no horizontal overflow, clipped primary content, obscured camera/model target, or inert control.
5. Open Play with Pippin and confirm its current UI and controls remain intact.

- [ ] **Step 4: Capture and inspect visual evidence**

Capture representative desktop and mobile composites to the two exact QA image paths. Use `view_image` on the generated source assets and both implementation screenshots in the same QA pass.

- [ ] **Step 5: Write the fidelity ledger**

Create `docs/qa/play-practice-animation-fidelity-ledger.md` with a table containing at least these comparison points for each game: approved copy, layout hierarchy, character/scene art, state reaction, palette/lighting, control readability, reduced-motion behavior, mobile crop, and fallback path. Each row must record spec evidence, render evidence, mismatch found, and fix applied or explicit intentional deviation.

- [ ] **Step 6: Confirm Pippin exclusion and review the final diff**

Run:

```powershell
git diff --name-only | rg -i 'pippin'
git diff --check
git status --short
```

Expected: the Pippin filter returns no files; `git diff --check` returns no new whitespace errors in changed implementation files; status contains only expected user-owned changes plus the planned new and modified files.
