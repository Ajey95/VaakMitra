# Play & Practice Four-Game Animation Upgrade Design

**Date:** 2026-08-05

**Status:** Approved and implemented

**Primary platform:** Existing React/Vite web application
**Audience:** Tamil-speaking children ages 3–10 and their caregivers

## 1. Goal

Upgrade four existing Play & Practice activities—Breath Balloon, River Rescue, Mouth Mirror, and Talk Together—into lively, expressive, reward-rich therapy experiences. Preserve their current functional flows, privacy safeguards, capability fallbacks, session reporting, and child-supportive language while making every interaction state visually clear and engaging.

Play with Pippin is explicitly excluded. Its route, behavior, visuals, tests, and assets must remain unchanged.

## 2. Product Principles

- Animation reinforces the therapy task; it never obscures instructions or rewards loudness over control.
- Every valid attempt receives an immediate, kind reaction.
- Idle scenes remain gently alive through breathing, blinking, swaying, water, weather, or ambient character movement.
- Success feedback appears at three scales: immediate reaction, completed-step celebration, and completed-session reward.
- Retry states are encouraging and never scary, punishing, or visually harsh.
- Tamil is the primary child-facing guidance language. Short English support may remain where the existing interface is bilingual.
- Camera frames, raw audio, and unrestricted transcripts are never stored.
- Motion and celebration respect the saved sensory preferences and `prefers-reduced-motion`.
- The target is smooth interaction on ordinary mobile and desktop hardware; visual complexity must scale down gracefully.

## 3. Scope

### Included

- Rich animated scenes for the four selected games.
- State-driven character expressions and environment reactions.
- Tamil prompt and encouragement copy for intro, active, retry, success, and completion states.
- Shared reusable ambient, particle, celebration, and status-animation primitives.
- Synchronized sound-effect hooks that obey the existing sound preference and browser autoplay rules.
- Responsive behavior for desktop, tablet, and mobile.
- Reduced and minimal motion variants.
- Unit and browser coverage for state-to-animation mappings, accessibility, and representative game flows.

### Excluded

- Any changes to Play with Pippin.
- Backend schema or API changes.
- New speech-recognition, breathing, or face-landmark models.
- Clinical claims or diagnostic scoring.
- Saving child audio, video, camera frames, or facial images.
- A new game engine, physics dependency, canvas-only rewrite, or large animation framework.
- Public leaderboards, purchases, or competitive rewards.

## 4. Technical Approach

Use a hybrid React, CSS, and raster-asset architecture.

- React owns semantic game state and selects named visual states such as `idle`, `listening`, `steady`, `too-strong`, `too-weak`, `retry`, `success`, and `complete`.
- Existing activity reducers, audio analysis, camera geometry, API calls, and reporting remain the source of truth.
- Small shared presentational components render ambient particles, celebration layers, Tamil voice prompts, and motion-safe state classes.
- CSS handles transforms, opacity, parallax, blinking, bobbing, ripples, swaying, and short character reactions. Animations use transform and opacity wherever possible.
- Generated raster assets provide production-quality characters, backgrounds, environmental layers, and reward props. Controls, labels, progress, focus states, and hit targets remain code-native.
- No new runtime animation dependency is required. Existing React and CSS conventions are retained.

Shared effects must accept a motion level and celebration level rather than independently reading storage. This keeps them deterministic, testable, and aligned with the existing interaction preference store.

## 5. Shared Visual System

### Ambient scene layer

The ambient layer supports clouds, sun rays, leaves, butterflies, sparkles, water glints, and room props. Each game selects only the effects appropriate to its setting. Decorative effects are `aria-hidden` and never intercept pointer events.

### Character state model

Characters receive a finite named mood rather than arbitrary animation flags:

- `sleepy`: intro-only awakening where specified.
- `idle`: breathing, blinking, and small orientation changes.
- `listening`: attentive eyes and restrained movement.
- `encouraging`: wave, nod, curious tilt, or gentle prompt.
- `surprised`: brief non-frightening response to excessive breath or input.
- `happy`: successful attempt reaction.
- `celebrating`: step or session completion sequence.

Animations return to `idle` after a bounded reaction so the UI does not accumulate conflicting classes.

### Celebration layer

The shared celebration layer supports stars, sparkles, confetti, balloons, stickers, coins, and fireworks. Each game configures a subset and intensity:

- `full`: complete particles and character reaction.
- `gentle`: fewer particles, no rapid flashes, reduced travel distance.
- `none`: static success badge and spoken/text praise only.

No effect flashes more than three times per second. The layer is non-interactive and removed when the reaction ends.

### Tamil guidance

Child-facing prompts are stored as explicit copy keyed by game state. Speech synthesis uses `ta-IN`, obeys the saved spoken-prompt and sound settings, starts only after an allowed user gesture, and cancels when the state changes or route exits. The visible status and spoken message must convey the same instruction.

## 6. Breath Balloon

### Scene and intro

The game opens in a bright layered meadow under a blue sky. Clouds drift, flowers and grass sway, birds cross occasionally, butterflies move near the foreground, and a smiling sun blinks. The balloon begins on the grass with sleepy eyes, yawns, stretches, becomes excited, and waves.

The intro prompt is: **“வணக்கம்! இன்று நம்ம பலூனை வானத்தில் பறக்க விடலாமா?”**

The current microphone privacy notice, two-second room calibration, screen-control fallback, and three-round structure remain intact.

### Input-to-animation mapping

- `idle` or no breath: the balloon gently bobs, blinks, smiles, looks around, and tilts with the breeze.
- `too-weak`: the balloon inflates slightly, wiggles, looks curious, and emits a few motivating sparkles. Prompt: **“சிறிது பலமாக முயற்சி செய்வோம்.”**
- `steady`: the balloon inflates smoothly; cheeks puff, the smile widens, eye highlights brighten, golden particles rotate, grass bends, flowers sway, and a wind swirl forms below it.
- `too-strong`: the balloon briefly shakes, looks surprised, spins once, and settles; nearby leaves move faster. Prompt: **“மிக வேகமாக இல்லை… மெதுவாக ஊதுங்கள்.”**
- breath stops before completion: the balloon settles downward without fully deflating and gives an encouraging wave. Prompt: **“பரவாயில்லை! இன்னும் கொஞ்சம் மெதுவாக ஊதலாம்.”**
- round success: the balloon reaches the glowing target band, collects a star, and rises into the next sky layer.

The existing calibrated normalized input determines these bands. Maximum volume never earns more points than stable target-zone control.

### Completion

After three rounds, the camera framing shifts upward as the balloon passes clouds, flies beside birds, crosses a rainbow, and collects floating stars. The final star triggers a bounded celebration with confetti, a dancing balloon, an opening treasure chest, coins, and the praise: **“அருமை! நீங்க ரொம்ப நல்லா செய்தீங்க!”**

## 7. River Rescue

### Scene and intro

The activity becomes a cohesive riverbank scene with a friendly baby elephant as the central character. The elephant approaches a flowing river with lowered ears and a concerned expression, then looks toward the child. Fish move below the water, dragonflies hover, trees sway, and sunlight glints on the river.

The intro prompt is: **“எனக்கு வீட்டிற்குச் செல்ல உதவுவாயா?”**

The existing five-step deterministic session, microphone fallback, help flow, and completion reporting remain intact. Current target words and step progression remain the source of truth.

### Attempt reactions

- `idle`: blinking, breathing, ear movement, trunk sway, flowing water, fish, and subtle reflections.
- `listening`: the elephant faces the child, raises its ears, and becomes still enough to show attention.
- `retry`: the next stone settles slightly, the elephant scratches its head and smiles, and the model mouth guidance becomes prominent. Prompt: **“பரவாயில்லை… இன்னொரு முறை முயற்சி செய்வோம்.”**
- `success`: the river glows; a stepping stone rises with golden light and a controlled splash; fish jump, a lotus blooms, and butterflies gather. The elephant claps, flaps its ears, sprays a small arc of water, and walks to the new stone.
- `complete`: the elephant reaches the far bank, turns toward the child, and celebrates beneath a rainbow with stars and confetti.

The retry animation must finish before the model demonstration begins, and the walking reaction must finish before the next spoken prompt. This prevents overlapping narration and visual state changes.

## 8. Mouth Mirror

### Scene

The camera/model area is framed as a magical mirror with a warm gold border, moving highlights, and restrained sparkles. A friendly cartoon speech therapist appears beside the model guide and demonstrates visible mouth shapes slowly: opening, smiling, lip rounding, lip closure, and cheek puffing where appropriate.

The existing five visible mouth targets, caregiver-approved camera gate, model-only fallback, landmark-derived geometry, and no-frame-storage promise remain unchanged. The design does not infer emotion or internal tongue placement.

### Feedback mapping

- `model`: the therapist performs the target movement at a deliberately slow pace with one literal Tamil instruction.
- `camera-waiting`: the mirror glows softly and gives neutral positioning guidance.
- `close`: the target outline becomes amber and the therapist nods encouragingly.
- `matched`: a green outline traces the visible mouth region, stars burst around the mirror, the therapist claps, and the prompt says **“சரியாக செய்தாய்!”**
- `retry`: the model movement replays more slowly with a single corrective cue such as open wider, close the lips, or round the lips.
- `complete`: the mirror shines, five target stars illuminate, and a gentle reward sequence plays.

Camera content remains unobscured. Decorative effects stay outside the central lip/jaw region and never cover permission or fallback controls.

## 9. Talk Together

### Mission environments

Each of the existing five caregiver-mediated missions receives a contextual illustrated environment:

1. Ask for water — home kitchen.
2. Choose between two snacks — grocery shop.
3. Find and name an object — classroom.
4. Take two imitation turns — park.
5. Say or select thank you — birthday room.

Hospital is retained as a future environment asset concept but is not added as a sixth mission in this upgrade.

### Turn and response animation

The current child prompt and discreet caregiver panel remain the interaction model. A soft glow, character gaze, and Tamil prompt identify whose turn it is. Characters blink, breathe, wave, nod while listening, point to relevant props, clap, and smile.

When the caregiver records a completed turn, the selected assistance level remains the reporting source of truth. Visual praise varies without changing the recorded result:

- independent: strongest character celebration plus stars and balloons.
- verbal or visual prompt: warm applause, stickers, and encouraging praise.
- modelled: shared character action followed by a gentle celebration.
- skipped: calm transition with no negative visual treatment.

Encouragement rotates among **“சிறப்பாக பேசினாய்!”**, **“மிகவும் அருமை!”**, and **“நீங்கள் தினமும் இன்னும் சிறப்பாக முன்னேறுகிறீர்கள்!”** The completion state combines the five earned mission stickers into one keepsake board.

## 10. Sound and Timing

- Ambient sound is optional and off until permitted by an interaction and saved preference.
- Short effects correspond to visible events: breath wind, stone rise, soft water splash, mirror sparkle, clap, sticker placement, and final reward.
- Speech guidance ducks optional ambient sound and never overlaps another spoken prompt.
- Route exit, pause, calm mode, or sound disable cancels pending speech and effects.
- Reaction timing is bounded: immediate feedback begins within 150 ms of known local state; ordinary reactions complete within 1.2 seconds; completion sequences may run up to 4 seconds and remain skippable.

## 11. Performance and Responsive Behavior

- Animate transforms and opacity instead of layout properties where possible.
- Limit simultaneous particles and reuse DOM nodes rather than continuously appending elements.
- Avoid per-frame React state updates for decorative motion.
- Keep generated images compressed and appropriately sized for mobile and desktop.
- Pause nonessential ambient animations when the page is hidden.
- Desktop and tablet show the full layered scene. Mobile reduces background objects, particle counts, and travel distances while keeping the primary character and action readable.
- Text and controls remain code-native, readable, and outside decorative art.
- Primary controls retain at least 44 × 44 CSS-pixel touch targets.

## 12. Accessibility and Sensory Safety

- `prefers-reduced-motion` and saved motion settings disable parallax, repeated bouncing, rapid confetti, and decorative travel.
- Minimal motion uses static state changes, opacity transitions, and clear text feedback.
- Success and retry states are announced through polite live regions and never rely on colour alone.
- Decorative assets use empty alternative text or `aria-hidden`; meaningful controls retain explicit accessible names.
- Focus order, keyboard operation, pause controls, and capability fallbacks remain available through every state.
- No intense screen shake, sudden zoom, frightening expression, loud error sound, or punitive visual is introduced.

## 13. Error Handling

- Microphone denial retains the current screen-control or caregiver fallback.
- Camera denial retains model-only Mouth Mirror practice.
- Failed speech evaluation preserves the attempt and offers retry, model guidance, caregiver confirmation, or skip according to the existing activity.
- Missing decorative art falls back to a stable colored scene without hiding controls or blocking progress.
- Failed optional sound playback does not block visual state changes.
- Animations interrupted by pause, route exit, or unmount clean up timers, speech, media, and temporary state classes.

## 14. Testing Strategy

### Unit and component tests

- Each semantic game state maps to the intended named visual state and Tamil prompt.
- Breath Balloon distinguishes weak, steady, excessive, stopped, and completed input without rewarding peak loudness.
- River Rescue sequences success animation, elephant movement, and the next prompt without overlap.
- Mouth Mirror displays matched, close, retry, camera-denied, and model-only states without covering the video or controls.
- Talk Together maps all five missions to environments and assistance levels to supportive reward intensity.
- Full, gentle, none, reduced-motion, and minimal-motion settings produce deterministic effect configurations.
- Play with Pippin files and tests remain outside the change set.

### Browser verification

- Complete representative success and retry flows in all four games with mocked media capabilities.
- Verify desktop and mobile layouts.
- Verify keyboard navigation, visible focus, live status announcements, pause, calm mode, and reduced motion.
- Verify denied microphone/camera and failed-evaluation fallbacks.
- Verify animation and speech cleanup after pause and route exit.
- Capture and visually inspect intro, active, retry, success, and completion states for each game.

## 15. Delivery Boundaries

Implementation must preserve the user's existing uncommitted work in the relevant pages and shared styles. Changes are applied incrementally around the current implementation rather than resetting or replacing those files.

The delivery sequence is:

1. Shared effects, state vocabulary, Tamil prompt helpers, and motion-safe styles.
2. Breath Balloon scene and reaction states.
3. River Rescue character, river, stepping-stone, and crossing states.
4. Mouth Mirror frame, therapist guide, and match feedback.
5. Talk Together mission environments, turn indicator, and rewards.
6. Cross-game sound, accessibility, responsive, performance, and regression verification.

## 16. Acceptance Criteria

- All four selected activities display lively idle scenes and distinct active, retry, success, and completion reactions.
- Tamil guidance matches the visible state and uses a warm, encouraging tone.
- Existing game mechanics, fallbacks, reporting, and privacy guarantees continue to work.
- Play with Pippin is unchanged.
- Full, gentle, none, reduced-motion, and minimal-motion settings visibly affect animations as specified.
- No child-facing failure state is frightening, punitive, or blocking.
- Decorative effects never obscure the therapy target, camera feed, instructions, or controls.
- The four activities work at desktop and mobile widths without overflow or clipped primary content.
- Relevant unit tests, browser tests, lint, and production build pass.
- Intro, active, retry, success, and completion screenshots are visually reviewed for all four games.
