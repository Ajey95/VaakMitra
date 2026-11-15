# SpeakEasy Interactive Child Experience Design

**Date:** 2026-08-01  
**Status:** Approved concept, pending written-spec review  
**Primary platform:** React/Vite web application with the existing FastAPI backend  
**Secondary platform:** Android remains compatible with the existing API, but feature parity is not part of this delivery

## 1. Goal

Transform SpeakEasy from a collection of mostly separate learning pages into a cohesive, child-led Tamil speech-practice experience for children aged 4–12. The application must react immediately to speech, touch, choices, and observable mouth movement while preserving predictable navigation, sensory control, privacy, and parent visibility.

The delivery contains six connected capabilities:

1. A shared interactive-session engine.
2. Persistent sensory and age-presentation settings.
3. One production-ready Voice Arcade game.
4. One production-ready Voice Quest story.
5. A Mouth Mirror for visible lip and jaw guidance.
6. An integrated Pippin companion plus Talk Together missions and parent reporting.

These are implemented as vertical slices over one shared engine rather than as six unrelated pages.

## 2. Product Principles

- Every child screen presents one primary task and no more than two simultaneous choices.
- The default interaction loop is **Choose → Listen → Try → React → Guide → Celebrate**.
- A valid communication attempt always receives an immediate, supportive response.
- Three unsuccessful attempts reveal support and allow progress; no child-facing failure state blocks the session.
- Rewards represent effort, communication turns, and personal improvement. There is no public child leaderboard.
- Motion, sound, spoken prompts, camera use, and session pace remain controllable.
- Child-facing experiences use simple, literal language and stable control positions.
- Camera frames and raw microphone recordings are not retained by the new features.
- Speech and movement results are practice feedback, not diagnosis or clinical claims.
- No unrestricted child-facing generative AI or open-ended chatbot is introduced.

## 3. Scope Boundaries

### Included

- React routes and components for the six capabilities.
- A shared session state machine and reusable feedback components.
- Local sensory/age preferences, with optional authenticated settings synchronization through the existing settings API.
- Backend event storage and parent roll-up reporting.
- Reuse of existing speech evaluation, Web Audio, browser speech synthesis, wallet, games, progress, and authentication infrastructure.
- Unit, component, API, integration, accessibility, and browser end-to-end tests.
- Responsive child screens for desktop/tablet and mobile widths.

### Excluded

- Unity LiveTalk integration and its multi-gigabyte model bundle.
- New speech-recognition or face-analysis ML model training.
- Clinical validation of pronunciation scores.
- Automatic emotion, stress, attention, or autism-severity inference.
- Reliable internal tongue tracking; Mouth Mirror is limited to visible lip and jaw geometry.
- Native Android UI parity in this iteration.
- Social features, public rankings, advertising, purchases, or real-money mechanics.

## 4. Information Architecture

The protected React application adds a child-focused **Play & Practice** entry point. It opens an activity home with six large destinations:

- Voice Quest
- Voice Arcade
- Mouth Mirror
- Pippin
- Talk Together
- My Progress

The existing adult dashboard remains available, but child sessions do not display the full adult sidebar. Interactive activities use a lightweight session shell containing:

- Home/exit control.
- Current activity title.
- A visual step sequence.
- Pause and sensory controls.
- One central activity region.
- One primary action.

## 5. Shared Interactive Session Engine

### 5.1 Domain model

`InteractiveSessionEngine` is a pure reducer-driven state machine. It does not directly call browser or network APIs.

States:

- `intro`: activity has not started.
- `prompting`: model audio/text/picture is presented.
- `ready`: the child may respond.
- `listening`: microphone or camera interaction is active.
- `evaluating`: local or remote evaluation is pending.
- `success`: the response met the current target.
- `support`: the response needs a hint or model.
- `complete`: all activity steps are finished.
- `paused`: activity is deliberately suspended.
- `error`: a recoverable capability or network error occurred.

Core events:

- `START`, `PROMPT_FINISHED`, `BEGIN_ATTEMPT`, `RESPONSE_CAPTURED`, `EVALUATION_SUCCEEDED`, `EVALUATION_RETRY`, `CAPABILITY_ERROR`, `USE_HINT`, `SKIP`, `NEXT_STEP`, `PAUSE`, `RESUME`, `COMPLETE`, `RESET`.

The engine tracks activity ID, step ID, attempt number, hints used, earned effort points, assistance level, elapsed active time, and an append-only event list. Attempt limits default to three but remain configurable per activity.

### 5.2 Activity definition

Activities use serializable definitions rather than custom navigation logic. Each definition includes:

- Stable activity and step identifiers.
- Age-band copy and optional image.
- Prompt text and speech language.
- Response mode: `choice`, `speech`, `airflow`, `mouth_shape`, `caregiver_confirm`, or `touch`.
- Evaluation rule and thresholds.
- Success, retry, hint, and skip responses.
- Next-step mapping.
- Reward value.

The engine exposes selectors for current prompt, progress, whether listening is allowed, whether the child may continue, and the child-safe feedback message.

### 5.3 Browser capabilities

Adapters isolate side effects:

- `speechInputAdapter`: existing MediaRecorder and browser speech-recognition behavior.
- `speechOutputAdapter`: browser speech synthesis with safe cancellation.
- `audioLevelAdapter`: normalized microphone energy after noise calibration.
- `mouthGeometryAdapter`: visible lip/jaw landmark measurements only.
- `sessionReportingAdapter`: sends a compact completed-session payload.

An unavailable adapter never crashes the activity. It produces a capability error with a fallback: typed/picture input, replayable model audio, caregiver confirmation, or skip.

## 6. Sensory and Age Settings

### 6.1 Age bands

- **Ages 4–6:** picture-first, minimal text, one short spoken instruction, large controls.
- **Ages 7–9:** picture plus short text, two-step prompts, visible personal progress.
- **Ages 10–12:** concise text, optional detailed feedback, self-management controls.

The registered child age selects the default band. A caregiver may override it because developmental presentation needs do not always match chronological age.

### 6.2 Sensory profile

Persist a versioned `interactionPreferences` object:

- `ageBand`: `early`, `middle`, or `older`.
- `soundEnabled`: boolean.
- `spokenPrompts`: boolean.
- `motionLevel`: `full`, `reduced`, or `minimal`.
- `celebrationLevel`: `full`, `gentle`, or `none`.
- `contrastMode`: `standard` or `high`.
- `sessionPace`: `guided` or `self`.
- `cameraEnabled`: boolean.

The first visit shows a caregiver-facing setup panel. Child sessions expose only pause, sound, and a calm-mode shortcut. `prefers-reduced-motion` sets the initial motion default unless a saved preference exists.

## 7. Voice Arcade Technical Proof: Breath Balloon

Breath Balloon is the first complete Voice Arcade game.

### Child flow

1. See the five-step visual schedule.
2. Tap Start and remain quiet for a two-second noise calibration.
3. Hear and see “Blow gently and keep it going.”
4. Microphone energy inflates a balloon continuously.
5. Energy below the calibrated threshold lets the balloon settle slightly; extreme peaks do not provide extra reward.
6. Hold the target zone for the required duration to complete the round.
7. Finish three short rounds and receive effort feedback plus a personal-best comparison.

### Rules

- Compute normalized level from smoothed analyser data relative to the calibrated noise floor.
- Target zone defaults to 0.25–0.70 normalized energy.
- Each round requires 1.5 seconds accumulated in the target zone.
- A round times out supportively after 20 seconds and offers retry or skip.
- The game never instructs a child to shout.
- Score is based on target-zone control and completed rounds, not maximum loudness.

### Persistence

Submit the existing game score payload using slug `breath-balloon`, duration, control accuracy, and level reached. Store the compact interactive-session report independently for parent reporting.

## 8. Voice Quest Demonstration: River Rescue

River Rescue is a deterministic five-step Tamil/English practice story in which the child helps Mitra guide a thirsty elephant to water.

Steps:

1. Choose the forest or river path using two picture choices.
2. Say the target vowel “A/அ” to call the elephant.
3. Say “Amma/அம்மா” or use the corresponding picture button to ask for help.
4. Sustain a gentle vowel to lower a bridge.
5. Choose and say a celebratory closing word.

Each step has early, middle, and older age-band copy. The story uses existing speech evaluation where a phoneme target exists and local duration/energy evaluation for sustained voice. If server evaluation fails, the child may retry locally or use caregiver confirmation. Story progress is kept locally until completion, then one compact report is submitted.

Visible story art uses cohesive production assets, while controls and text remain code-native. Motion responds to sensory settings.

## 9. Mouth Mirror

Mouth Mirror teaches visible articulatory positions for five initial profiles: open vowel, long open vowel, closed lips/hum, lip pop, and rounded lips.

### Child flow

1. Select a target sound.
2. View a model mouth image/video and one literal instruction.
3. Enable the camera after a caregiver-approved setting check.
4. See a mirrored feed with a simple target outline.
5. Receive real-time geometry feedback: open wider, close lips, round lips, or hold.
6. Hold the target zone for 600 ms to complete an attempt.
7. Receive a best-attempt summary without saving frames.

### Geometry

Use face landmarks only for mouth width, mouth height, normalized opening ratio, and lip closure. Do not calculate or display emotion, stress, focus, engagement, or internal tongue position. If landmarks are unavailable, show model-and-practice mode without scoring.

## 10. Pippin Integration

Pippin becomes an authenticated route inside the main application and uses the shared sensory profile.

Supported interactions:

- Tap/pet Pippin.
- Speak or select one of a curated set of safe commands.
- Hear Pippin repeat a recognized phrase.
- Receive a deterministic expansion for known single words, such as “ball” → “Yes, a red ball!”
- Perform commands: jump, dance, sleep, eat, hello, ball, and five initial Tamil practice words.
- Use picture-command buttons when speech recognition is unsupported or unwanted.

Pippin records only aggregate interaction events and vocabulary identifiers, never arbitrary transcript history on the server. A local recent-history list may contain up to five entries and is cleared on route exit or explicit reset.

## 11. Talk Together

Talk Together contains caregiver-mediated missions designed to transfer practice into real interaction.

The initial pack contains five missions:

- Ask for water.
- Choose between two snacks.
- Find and name a familiar object.
- Take two imitation turns.
- Say or select “thank you.”

Each mission displays one child prompt and a discreet caregiver panel. The caregiver can mark `independent`, `verbal_prompt`, `visual_prompt`, `modelled`, or `skipped`. Caregiver confirmation advances the session and is the source of the recorded assistance level. No microphone or camera is required.

## 12. Parent Reporting

### API

Add authenticated endpoints:

- `POST /api/interactive-sessions`: validate and store one completed or deliberately exited session summary.
- `GET /api/interactive-sessions/summary`: return the current child’s recent activity totals and assistance trend.

Stored fields:

- User ID, activity ID/type, started/completed timestamps.
- Completed steps and total steps.
- Communication turns, successful turns, attempts, hints, and skips.
- Assistance-level counts.
- Duration and earned effort points.
- Optional game score ID.
- No raw audio, video, arbitrary transcript, or facial frames.

### Parent UI

Add an **Interactive Practice** section to the existing Parent Dashboard showing:

- Sessions this week.
- Communication turns.
- Independent-turn percentage.
- Most-practised activity.
- Assistance trend for the last seven sessions.
- A short recommendation derived from aggregate data.

When no sessions exist, show a truthful empty state; do not fall back to fabricated statistics.

## 13. Error Handling

- Microphone denied: explain the requirement and offer picture/caregiver input.
- Camera denied or unavailable: keep model-only Mouth Mirror practice usable.
- Browser speech recognition unavailable: retain recording/evaluation where supported and picture-command alternatives.
- Network evaluation fails: do not discard the attempt; offer local retry, caregiver confirmation, or skip.
- Reporting fails: queue one minimal summary in versioned local storage and retry on the next authenticated app start.
- Invalid activity definitions: fail closed to the activity home and report a developer-visible error without exposing technical text to the child.
- Route exit: stop tracks, cancel speech synthesis, close audio contexts, and present an exit/save summary.

## 14. Accessibility and Privacy

- All primary controls are keyboard accessible and have visible focus.
- Touch targets are at least 44 × 44 CSS pixels.
- Status changes use polite live regions and do not rely only on colour.
- Reduced/minimal motion disables nonessential bouncing, confetti, parallax, and continuous decorative animation.
- No autoplay sound occurs before a user gesture unless browser policy and the saved caregiver setting both allow it.
- Camera and microphone indicators remain visible while active.
- Settings use privacy-preserving defaults.
- The implementation must not claim to diagnose pronunciation disorders, emotional state, stress, or autism severity.

## 15. Testing Strategy

### Unit tests

- Reducer transitions, attempt limits, hints, skip behavior, pause/resume, completion, and reset.
- Age-band copy selection and preference migration.
- Audio calibration and normalized target-zone scoring.
- Quest branching and deterministic fallback rules.
- Mouth geometry classification using fixture landmarks.
- Pippin intent matching, response expansion, and history limit.
- Talk Together assistance aggregation.
- Parent summary calculations and API validation.

### Component tests

- Session shell progress and calm-mode controls.
- Permission-denied fallbacks.
- Voice Arcade start/calibrate/play/complete states.
- Voice Quest choice and speech retry states.
- Mouth Mirror model-only and camera states.
- Pippin touch, picture-command, listening, and reset states.
- Talk Together caregiver confirmation.
- Parent reporting empty and populated states.

### Backend tests

- Authentication is required.
- A user can write/read only their own summaries.
- Raw media/transcript fields are rejected.
- Counts and ranges are validated.
- Roll-ups are correct and empty data stays empty.

### Browser tests

- Complete all six workflows with mocked media capabilities.
- Verify desktop and mobile layouts.
- Verify keyboard navigation and reduced-motion behavior.
- Verify denied microphone/camera and failed-network recovery.
- Verify tracks/audio contexts are released after exit.
- Verify completed data appears in Parent Dashboard.

### Regression checks

- Existing frontend unit tests.
- Frontend lint and production build.
- Existing backend test suite, with the Python 3.12 event-loop test compatibility issue fixed as a prerequisite.
- Android build to confirm shared API changes are backward compatible.

## 16. Delivery Sequence

1. Shared engine, activity schema, sensory/age settings, and session shell.
2. Backend interactive-session storage and roll-up API.
3. Breath Balloon Voice Arcade vertical slice.
4. River Rescue Voice Quest vertical slice.
5. Mouth Mirror.
6. Pippin integration.
7. Talk Together and Parent Dashboard reporting.
8. Full accessibility, responsive, regression, and browser verification.

Each stage must leave the application working and independently testable. Production code follows red-green-refactor: a failing test is written and observed before implementation for every behavior change.

## 17. Acceptance Criteria

The work is complete only when:

- All six capabilities are reachable from the authenticated web application.
- Each primary workflow completes without placeholder toasts or inert controls.
- Age and sensory preferences visibly alter copy, motion, celebration, sound, and pace as specified.
- The new activities work with their documented media fallbacks.
- No new feature stores raw child audio, video, arbitrary transcripts, or facial frames.
- Parent reporting displays real new-session data and a truthful empty state.
- Public child ranking is absent from the new experience.
- Automated emotion/stress labels are absent from Mouth Mirror.
- New unit, component, API, and browser tests pass.
- Existing frontend, backend, and Android regression checks pass, except for a clearly documented external-toolchain blocker that cannot be corrected inside the repository.
- Desktop and mobile screenshots have been visually inspected against the approved design concepts.

