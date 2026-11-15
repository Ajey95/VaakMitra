# 3D Character Coach Design

Date: 2026-08-02
Status: Approved

## Objective

Turn Pippin and Kavi from mostly static activity art into responsive child-training hosts. Each character must initiate a short prompt, visibly wait for a response, accept voice or touch alternatives, react kindly, model a word after difficulty, and celebrate effort. The interaction should resemble the clear call-and-response rhythm of a preschool television host without copying any protected character, dialogue, or visual design.

## Product boundaries

- Pippin receives a playful `Cute Kitten` voice and a quieter `Gentle` voice option.
- Kavi receives a slower, warm young-elephant voice.
- Dialogue is curated and deterministic. No unrestricted language-model conversation is introduced.
- The child can always use voice, a picture, touch, repeat, or gentle skip.
- No audio, transcript, video, face data, or arbitrary child phrase is included in reporting.
- Existing age, calm-mode, sound, spoken-prompt, and reduced-motion preferences remain authoritative.
- WebGL failure must leave a useful 2D character experience.

## Architecture

### Character voice module

`characterVoice.js` owns voice profiles and browser speech construction. Profiles provide language, pitch, rate, volume, and preferred installed-voice hints. Runtime values are clamped to safe browser ranges. `Cute Kitten` uses a higher pitch and light pace; `Gentle` uses a softer neutral profile; Kavi is slower and lower. If browser speech is unavailable, visible bubbles and all training controls remain usable.

### Dialogue coach engine

`characterCoach.js` defines finite missions and pure state transitions. A mission moves through `intro`, `prompt`, `listening`, `thinking`, `success`, `support`, and `complete`. Events include `START`, `PROMPT_FINISHED`, `BEGIN_LISTENING`, `ANSWER`, `NO_ANSWER`, `USE_PICTURE`, `TRY_AGAIN`, `SKIP`, and `NEXT`. The engine never produces open-ended content; every spoken response comes from reviewed mission data.

Pippin missions cover greeting, choosing a toy, family words, an action word, and a friendly finish. Kavi continues the River Rescue sequence but speaks before each turn and reacts immediately to the child’s response.

### Shared 3D stage

`CharacterStage3D.jsx` renders lightweight procedural characters with React Three Fiber. The kitten and elephant are composed from basic geometry and materials so the app does not depend on an unlicensed or missing GLB file. Character state controls ears, head tilt, trunk/tail, bobbing, eye expression, listening lean, speaking mouth movement, and celebration motion.

Motion is minimal when reduced-motion or calm mode is active. A WebGL capability check and React error boundary switch to the existing Pippin image or River Rescue artwork when 3D cannot render. The fallback still displays character state and dialogue.

### Activity integration

Pippin becomes a five-turn coach rather than a free-form microphone panel. Voice and picture modes remain, but the current mission prompt is always explicit. The child can hear the prompt again, switch voice profile, answer, ask for help, or skip gently.

Kavi appears as a 3D overlay within the existing River Rescue story world. Existing scoring and reports remain intact. Character mood maps directly to activity mode: prompt to speaking, recording to listening, checking to thinking, retry to encouraging, and completion to celebrating.

## Voice behavior

- `kitten`: pitch 1.55, rate 1.02 or 0.94 in guided pace, volume 0.92.
- `gentle`: pitch 1.16, rate 0.94 or 0.86 in guided pace, volume 0.88.
- `kavi`: pitch 0.92, rate 0.88 or 0.80 in guided pace, volume 0.95.
- Prefer an installed `en-IN` voice, then any English voice, then the browser default.
- Speech is cancelled before a new line and whenever the activity unmounts.
- Voice selection is stored only as an allow-listed preference; spoken text and recognized text are not persisted.

## Interaction and support policy

- Prompts contain one action and at most two choices.
- A child is never marked wrong for silence or recognition failure.
- First difficulty produces a shorter prompt; second difficulty exposes a model/picture response.
- Every attempt receives neutral or positive feedback.
- Touch alternatives are equal communication, but assistance reporting distinguishes independent voice from visual support.
- The character never asks for personal information and never repeats unsafe arbitrary phrases.

## Accessibility and performance

- Controls retain 44 px minimum targets, keyboard operation, accessible labels, visible focus, and live status text.
- 3D is lazy-loaded only on Pippin and River Rescue routes.
- Geometry and materials are memoized, shadows are limited, device pixel ratio is capped, and no remote model is loaded.
- Mobile stacks character and controls without horizontal scrolling.
- Calm mode disables celebration particles, continuous floating, and automatic voice.

## Reporting and privacy

Existing interactive-session payloads remain counts-only. New metadata is not required. The server receives activity ID, turns, successes, attempts, assistance counts, bounded duration, and effort points. Voice profile, transcript, installed browser voice, and raw microphone data remain local.

## Error handling

- Microphone denial switches to picture input without losing the mission.
- Speech-synthesis failure leaves the visible prompt and a disabled replay state.
- WebGL/context failure switches to 2D fallback.
- API/report failures never block the child’s completion screen.
- Leaving an activity stops microphone tracks, speech recognition, speech synthesis, and animation timers.

## Verification

- Unit tests for voice profiles, clamping, installed-voice selection, mission transitions, retry/support behavior, and report privacy.
- Component/browser tests for voice selection, prompt replay, picture fallback, microphone denial, Kavi reactions, 3D fallback, reduced motion, mobile overflow, and cleanup.
- Full Vitest, ESLint, Vite build, Playwright, backend Pytest, and Android regression matrix before completion.

## Success criteria

Pippin and Kavi visibly lead the interaction, wait for the child, respond to at least voice and touch input, speak with distinct safe profiles, animate according to conversational state, remain usable without media or WebGL permission, and preserve the project’s counts-only privacy contract.
