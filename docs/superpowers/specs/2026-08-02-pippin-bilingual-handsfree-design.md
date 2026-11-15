# Pippin bilingual hands-free design

## Goal

Make Pippin a safe, friendly English–Tamil speaking companion. After one browser-required microphone permission action, Pippin listens without per-turn Start/Stop controls, detects when the child has finished, repeats the same local recording with a bright kitten-style effect, and automatically listens for the next turn.

## Approaches considered

1. **Local recorder plus voice-activity detection (selected).** Record in the browser, detect speech energy and 3.5 seconds of silence, replay locally, then re-arm. This preserves the child's exact words and keeps audio on the device.
2. Browser speech recognition plus text-to-speech. This can change the child's words, is browser-dependent, and may send audio to a browser service, so it does not meet the exact-repeat and privacy goals.
3. Push-to-talk. This is simpler but conflicts with the requested hands-free child interaction.

## Interaction flow

1. The page initially shows one bilingual `Enable microphone / மைக்ரோஃபோனை இயக்கவும்` action. This is permission activation, not a recording Start/Stop control.
2. After permission is granted, Pippin enters `Listening / கேட்கிறேன்` and the permission action disappears.
3. Silence is ignored until voice has first been detected. Active speech continually resets the silence timer.
4. After 3.5 seconds of silence, Pippin stops that turn and shows `Getting ready / தயாராகிறேன்`.
5. Pippin replays the local audio with the kitten effect while its mouth, eyes, and body animate.
6. After playback completes, Pippin automatically begins the next listening turn.
7. A maximum-turn timer protects against endless recording in noisy rooms. Navigation, reset, Dance, and Sing dispose the active recorder/playback cleanly.
8. If microphone permission fails, Pippin shows a bilingual explanation and safe bilingual phrase buttons.

## Detection and replay

- Use the existing microphone `AnalyserNode`; no speech-to-text service is involved.
- Encapsulate turn detection in a pure state machine so speech start, silence, reset, and maximum duration can be tested deterministically.
- Required silence: 3,500 ms after speech is detected.
- A bounded adaptive noise floor prevents ordinary room noise from keeping a turn open.
- A short minimum speech duration rejects clicks and microphone pops.
- A maximum turn duration prevents indefinite capture.
- The replay remains local. A moderately increased playback rate plus gentle high-frequency shaping and compression creates a bright, cute kitten character without claiming to clone or identify a person's gender.

## Bilingual presentation

Every Pippin-specific title, instruction, status, action, fallback phrase, accessibility label, and privacy message shows English and Tamil together. Tamil script is paired with readable English rather than transliteration-only content. Kavi's separate Tamil learning story is unchanged.

## Privacy, safety, and reporting

- Raw audio and recognized words never leave the page and are never stored.
- No child transcript is created for Pippin.
- Reports contain only aggregate turn count and duration.
- Microphone tracks, audio contexts, animation frames, and timers are released on exit or failure.
- Dance and Sing remain optional, bilingual side activities and never compete with an active recording.

## Verification

- Unit tests for the turn detector: no trigger before speech, short noise rejection, 3.5-second silence trigger, speech-resume reset, maximum duration, and reset.
- Unit tests for the replay graph and fallback playback rate.
- Component/browser tests for the one-time permission action, absence of Start/Stop controls, bilingual status, auto-stop, auto-replay, and auto-relisten.
- Regression tests for privacy reporting, permission denial, Dance/Sing, responsive layout, lint, production build, and the full frontend suite.
