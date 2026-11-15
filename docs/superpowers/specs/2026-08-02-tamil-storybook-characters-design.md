# Tamil Storybook Characters Design

## Goal

Replace the uncanny procedural 3D Pippin and Kavi models with warm, flat SVG storybook characters. Kavi becomes a five-page Tamil speech-learning story that evaluates recorded attempts. Pippin becomes a privacy-preserving Tamil repeat companion that plays the child's own recording back with a gentle kitten effect.

This is a learning game, not a diagnostic or clinical assessment. Feedback is encouraging and never labels a child, attempt, or pronunciation as bad or wrong.

## Design principles

- All child-facing Kavi story copy, prompts, buttons, hints, and spoken feedback are Tamil.
- Characters use large rounded shapes, soft colors, visible smiles, slow blinks, and small predictable movements.
- No WebGL, 3D models, remote character files, or uncanny realistic motion.
- Every microphone interaction has replay, retry, picture/model help, and skip support.
- Kavi evaluates bounded recordings; Pippin repeats locally and never uploads its recording.
- Reduced-motion and calm modes stop decorative movement while preserving state communication.
- Raw recordings and transcripts are never written to progress reports or browser storage.

## Kavi: five-page Tamil crossing story

Kavi is a friendly baby elephant trying to cross a river to reach his family. Each successful speech turn changes the SVG world and advances one story page.

| Page | Learning level | Target | Tamil narration | Story change |
|---|---|---|---|---|
| 1 | Short vowel | `அ` | `கவி ஆற்றங்கரையில் நிற்கிறான். பாதையைத் திறக்க “அ” என்று சொல்லலாமா?` | A closed flower opens and reveals the first stepping stone. |
| 2 | Long vowel | `ஈ` | `மின்மினிப் பூச்சிகள் வழி காட்ட வேண்டும். “ஈ” என்று நீளமாகச் சொல்லுங்கள்.` | Fireflies light a safe route toward the bridge. |
| 3 | Word | `அம்மா` | `கவி தன் அம்மாவை அழைக்க வேண்டும். “அம்மா” என்று சொல்லுங்கள்.` | Kavi's family appears across the river and waves. |
| 4 | Phrase | `கவி வா` | `பாலம் அருகே வந்துவிட்டது. “கவி வா” என்று அழையுங்கள்.` | The bridge lowers and Kavi walks to its entrance. |
| 5 | Sentence | `கவி பாலத்தைக் கடக்கலாம்` | `கவி பாலத்தைக் கடக்கத் தயாராக இருக்கிறான். “கவி பாலத்தைக் கடக்கலாம்” என்று சொல்லுங்கள்.` | Kavi walks across the bridge and the family celebrates. |

The child starts a page, hears the modelled target, records an attempt, submits it for evaluation, receives spoken Tamil feedback, and either retries or turns the page. After three supported attempts, picture/model help permits progression without a failure label.

Core Tamil controls are `கதையைத் தொடங்கு`, `கேளுங்கள்`, `பேசத் தொடங்கு`, `முடித்தேன்`, `மீண்டும் முயற்சி`, `பட உதவி`, `அடுத்த பக்கம்`, and `கதையை முடிக்க`.

## Kavi SVG scene and motion

`KaviStorybookScene` owns only presentation. It receives the current page, character mood, progress, message, audio level, and sensory motion level.

The SVG contains reusable groups for sky, hills, river, plants, stepping stones, family, bridge, sparkles, and Kavi. Page state controls visibility and positions; it does not replace the whole illustration with unrelated images. Kavi has separate eye, pupil, eyelid, mouth, ear, trunk, legs, and tail groups.

Character states are:

- `idle`: slow blink and very small breathing motion.
- `speaking`: mouth opens from narration audio timing; trunk moves slightly.
- `listening`: pupils face the child; ears lift once.
- `thinking`: eyes look upward; a small Tamil ellipsis bubble appears.
- `encourage`: smile, head tilt, and one heart.
- `celebrate`: two gentle hops and bridge/story progression.
- `walking`: alternating legs and horizontal progress toward/across the bridge.

Mouth animation is driven by narration playback state or live analyser level. Minimal motion freezes breathing, walking tween frames, sparkles, and decorative loops at readable poses. SVG text remains HTML outside the illustration for accessibility and translation reliability.

## Tamil speech evaluation

The current English `facebook/wav2vec2-base-960h` path is not used for this story. Unknown targets must never silently reuse the `அ` acoustic template.

Evaluation uses two bounded strategies behind one `TamilStoryEvaluator` interface:

1. Pages 1–2 use vowel acoustics: non-silence duration, energy, and target-specific MFCC/formant similarity for `அ` and `ஈ`. Browser Tamil speech recognition can contribute evidence but is not required for isolated vowels.
2. Pages 3–5 use Tamil ASR plus normalized target similarity. The default lazy-loaded model is `vasista22/whisper-tamil-small`, a Whisper Small model fine-tuned on multiple public Tamil ASR corpora. The model ID is configurable for deployments with different resource budgets.

Tamil normalization removes punctuation and spacing differences while preserving Tamil code points. Word scoring checks target token coverage and edit similarity. Phrase and sentence scoring allow small ASR variations but require the important target tokens. The response contract includes bounded accuracy, matched status, evaluation method, and one Tamil feedback key. It does not return diagnostic claims.

If the Tamil model is unavailable, the API returns a capability status instead of a fabricated score. The UI then uses browser Tamil transcription when available or offers modelled/picture support and retry. Model loading is lazy so normal backend startup remains responsive.

The recording endpoint retains its authentication, content-type allow-list, upload size limit, rate limit, and in-memory processing. Child audio and transcripts are not logged or stored by the story/reporting layer.

## Voice system

Kavi uses a finite set of Tamil narration and feedback lines. The preferred production voice is an original, non-cloned young storybook character voice generated through ElevenLabs multilingual Tamil TTS. Only fixed application-authored Tamil strings are eligible for that provider. Audio is cached by a server-side allow-listed line ID; arbitrary child text is rejected.

The TTS adapter is optional and configured only through server environment settings. When it is unavailable, the app selects an installed `ta-IN` voice, preferring a native Tamil female voice such as Pallavi when the operating system provides one. The fallback uses natural rate and only a mild pitch lift; it does not use the previous extreme kitten pitch.

Fixed feedback includes `அருமை!`, `மிக நன்று!`, `நல்ல முயற்சி! இன்னொரு முறை சொல்லலாமா?`, and `நாம் சேர்ந்து முயற்சி செய்வோம்.` Speech is cancelled before a new line and on page exit.

## Pippin: Tamil repeat-and-play companion

Pippin has no scoring or lesson progression. The child taps `பேசலாம்`, records any short Tamil phrase, and taps `முடித்தேன்`. Pippin immediately repeats the exact local recording through a Web Audio graph with a mild playful pitch/playback transformation. The original blob is revoked after playback/reset and is never uploaded or persisted.

Pippin's SVG has rounded kitten features, a blue scarf, blinking eyelids, tracking pupils, smile/talking mouth shapes, swaying tail, and three explicit play actions:

- `மீண்டும் சொல்`: repeat the latest local recording.
- `ஆடு`: a short side-to-side dance with music-note shapes.
- `பாடு`: a short fixed Tamil melody using bundled tones and the character mouth animation.

The live audio analyser drives Pippin's mouth while listening and replaying. If Web Audio processing is unavailable, the original local recording plays without transformation. If recording is denied, Pippin presents large Tamil picture/phrase buttons and repeats their fixed Tamil labels with the safe voice system.

## State and data flow

Kavi's pure story reducer owns `intro`, `narrating`, `ready`, `listening`, `evaluating`, `support`, `success`, `walking`, and `complete`. It stores the page index, attempt count, assistance level, and aggregate success count. Audio blobs stay in component memory until evaluation finishes and are then reset.

Pippin owns `idle`, `listening`, `replaying`, `dancing`, and `singing`. Its latest blob and audio nodes are held in refs, not Zustand or storage. Leaving either page cancels TTS, recognition, media tracks, timers, animation frames, and audio nodes.

Kavi reports aggregate turns, successes, attempts, assistance counts, duration, and effort points through the existing interactive-session API. Pippin reports only aggregate repeat/play counts. Neither report contains target text, transcript, audio, generated provider data, or a child name.

## Visual system

- Illustration: flat children's-book vector art with rounded geometry and visible outlines.
- Palette: river teal, leaf green, warm mango, lavender, and cream; no dark realistic shading.
- Layout: open storybook spread on desktop and a single vertical page on mobile.
- Type: existing rounded application typography with larger Tamil line height and no text embedded in SVG paths.
- Controls: minimum 48px targets, visible focus rings, short Tamil labels, and persistent picture help.
- Progress: five illustrated page dots rather than a clinical score meter.

## Error handling

- Microphone denied: explain in Tamil and reveal picture/model help immediately.
- Empty or too-short recording: do not submit; invite another gentle try.
- Model unavailable or request timeout: no zero score; offer browser recognition/modelled support.
- Low-confidence attempt: say `நல்ல முயற்சி!` and show listen/retry/help choices.
- TTS unavailable: keep all Tamil copy visible and continue silently.
- SVG/CSS animation unavailable: render stable smiling character poses.

## Testing and acceptance

- Pure unit tests cover all Kavi reducer transitions, five fixed targets, Tamil normalization/similarity, vowel routing, Tamil ASR routing, model-unavailable behavior, and aggregate-only reports.
- Voice tests enforce allow-listed Kavi line IDs and reject arbitrary text from the external TTS adapter.
- Pippin tests prove local recording replay never calls evaluation, upload, or TTS APIs and releases audio resources.
- Browser tests verify all five Tamil pages, success/retry/help paths, Kavi bridge movement, SVG mouth/eye states, Pippin repeat/dance/sing, microphone denial, keyboard use, calm/reduced motion, mobile overflow, and absence of canvas/WebGL.
- Backend tests retain authentication, upload limits, content types, rate limiting, and no raw child-data storage.
- Visual QA compares approved storybook concepts with desktop and mobile screenshots and rejects character/control overlap, clipped Tamil text, unreadable scene changes, or uncanny shading.

## Explicit exclusions

- No clinical diagnosis, disorder prediction, or claim of phoneme-level medical accuracy.
- No open-ended chatbot or generative child conversation.
- No cloning of a real child's, celebrity's, or copyrighted character's voice or appearance.
- No external TTS request containing a child's recording, transcript, name, or arbitrary phrase.
- No camera requirement, leaderboards, negative scoring, or punitive animation.
