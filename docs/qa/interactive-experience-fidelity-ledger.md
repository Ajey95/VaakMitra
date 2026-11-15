# Interactive experience visual fidelity ledger

Reviewed on 2026-08-01 against `docs/design/interactive-child-experience-concept.png` at 1440×1000 desktop and 390×844 mobile viewports.

## Shared shell and Play & Practice home

- Preserves the concept's indigo, cyan, green, coral, and amber activity coding while fitting the existing SpeakEasy dashboard shell.
- Replaces the concept's dense six-picture grid with one featured activity and five generously spaced cards; this improves scanning and touch accuracy on small screens.
- Keeps the concept's child-directed invitation and adds explicit permission to pause, ask for help, or use a picture.
- Carries Calm, sensory settings, pause, back navigation, and the visual schedule consistently into every activity.
- Mobile capture has no horizontal overflow; cards become a single readable column and retain large touch surfaces.

## Breath Balloon

- Retains the concept's single-object, microphone-led arcade loop and three-stage journey.
- Adds a room-noise calibration gate before play so a noisy environment cannot accidentally score as success.
- Replaces “blow harder” pressure with calm-zone language and explicitly avoids rewarding shouting.
- Keeps the privacy message adjacent to the microphone action: sound is processed live and not saved.
- Desktop and mobile captures preserve a centered task, large action target, uncluttered background, and permanently reachable calm/pause controls.

## River Rescue

- Closely matches the concept's friendly elephant, river, bridge, and storybook setting using one cohesive generated scene rather than mixed stock art.
- Uses a five-step visual schedule matching the concept's choose/listen/try/celebrate rhythm.
- Limits each decision to two safe choices and states that both paths are safe, preventing failure anxiety.
- Supports voice, breath, and pointer fallbacks without displaying or persisting the child's recognized phrase.
- On mobile the illustration crops cinematically around Kavi and the bridge while both decision buttons remain fully visible and comfortably tappable.

## Mouth Mirror

- Preserves the concept's watch-and-copy goal but introduces a privacy-first mode chooser before camera activation.
- The default path works with an illustrated mouth model; camera access is optional and requested only for the current activity.
- Camera frames remain local and temporary, with the guarantee displayed directly above the choices.
- Evaluation is restricted to simple face presence and mouth geometry; no emotion, stress, identity, or diagnostic inference is shown.
- Five visible practice steps, 600 ms holds, model-only fallback, and calm/pause controls work identically at desktop and mobile widths.

## Pippin

- Retains the concept's warm orange companion and creates the strongest character-led surface in the implemented set.
- Provides voice and picture tabs plus petting/tapping, so interaction is not blocked by speech recognition.
- Uses curated safe intents (including Tamil family words) and a neutral repeat prompt for unknown speech.
- Keeps the child's last five local turns only in the active tab and sends counts—not words—to reporting.
- Mobile stacks the mascot and controls without shrinking Pippin or the microphone target; privacy language remains visible without opening a menu.

## Talk Together

- Preserves the concept's co-play purpose while avoiding camera capture entirely.
- Uses five short, concrete missions and counts words, gestures, pictures, and sounds equally as communication.
- Makes caregiver guidance discreet and collapsed by default so the child's prompt stays dominant.
- Offers “We had a turn” and “Skip gently,” avoiding pass/fail framing and forced performance.
- Desktop and mobile maintain one task card, one prominent positive action, large targets, and visible calm/pause controls.

## Parent reporting

- Adds Play & Practice reporting to the existing parent dashboard instead of creating a disconnected second reporting system.
- Shows loading, error, empty, and populated states; the reviewed empty state truthfully says there are no sessions yet.
- Reports only bounded summary metrics: sessions, turns, independence, most-practised activity, assistance trend, and a recommendation.
- Does not expose recordings, camera frames, recognized phrases, or transcripts.
- Mobile retains all dashboard content in one column without horizontal clipping; the new summary appears near the top where caregivers can find it quickly.

## Outcome

All seven major surfaces passed direct screenshot inspection at both target viewports. No blocking overlap, clipped action, unreadable text, horizontal overflow, or visual privacy ambiguity was observed.
