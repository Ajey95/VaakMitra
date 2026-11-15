# Tamil Storybook Verification

Verified on 2026-08-02 against the local frontend at `http://127.0.0.1:5173` and API at `http://127.0.0.1:8001`.

## Navigation

1. Register at `/register` or sign in at `/login`.
2. Open `/play` from the authenticated application.
3. Choose **River Rescue** to open Kavi at `/play/quest/river-rescue`.
4. Choose **Play with Pippin** to open Pippin at `/play/pippin`.

## Kavi

- Friendly inline SVG baby elephant; no Canvas, WebGL, or 3D stage on the route.
- Five Tamil pages in order: `அ`, `ஈ`, `அம்மா`, `கவி வா`, `கவி பாலத்தைக் கடக்கலாம்`.
- Local acoustic evaluation routes the two isolated vowels; a lazy Tamil Whisper adapter routes the word, phrase, and sentence.
- Three supported attempts reveal a modelled picture prompt; capability loss reveals support rather than a fabricated score.
- Optional fixed-line cute narration uses the authenticated story-voice endpoint. Without provider configuration, the browser uses an installed `ta-IN` voice.
- Reports contain only backend-approved aggregate counts and timestamps.

## Pippin

- Friendly inline SVG kitten with blinking eyes, speaking mouth, smile, scarf, and moving tail.
- Every Pippin title, instruction, status, action, fallback, privacy notice, and accessibility description displays English and Tamil together.
- A single bilingual microphone-permission action activates hands-free turns; no per-turn Start or Stop controls are present.
- Sustained speech activates the turn detector. Exactly 3.5 seconds of silence ends the turn, local replay follows, and the next recording opens automatically.
- The latest recording stays in memory and is decoded/replayed locally at `1.24` playback rate through a gentle high-shelf, compressor, and gain chain for a bright kitten-style effect.
- The recording, transcript, and child text are never sent to evaluation, upload, or external TTS endpoints.
- Dance and song actions are local. Microphone denial reveals fixed bilingual phrase buttons.
- Reports contain aggregate repeat counts only.

## Configuration

- `ELEVENLABS_API_KEY` and `ELEVENLABS_STORY_VOICE_ID` are optional server-only environment variables.
- When either value is absent or the provider fails, narration falls back to native Tamil speech.
- The Tamil ASR model `vasista22/whisper-tamil-small` loads lazily on the first word/phrase/sentence evaluation. Tests inject a transcriber and do not download the model.
- No application endpoint accepts arbitrary external-TTS text.

## Automated results

- Frontend unit: 20 files, 117 tests passed.
- Frontend lint: passed with zero warnings.
- Frontend production build: passed.
- Playwright: 15 browser journeys passed, including four registration journeys, full five-page Kavi completion, Pippin's 3.5-second auto-stop/replay/relisten flow, permission-request concurrency protection, denied-microphone support, keyboard use, reduced motion, privacy, and 390px layouts.
- Backend: 100 tests passed.
- Python compilation: passed.
- Python production dependency audit: no known vulnerabilities after replacing the unused `python-jose`/`ecdsa` dependency with PyJWT.
- npm audit: two high findings remain in React Router's unstable RSC API path. This Vite SPA does not use React Server Components or server actions; the upstream advisory explicitly limits impact to unstable RSC APIs.

## Visual inspection

- [Kavi desktop](./kavi-storybook-desktop.png)
- [Kavi mobile](./kavi-storybook-mobile.png)
- [Pippin desktop](./pippin-storybook-desktop.png)
- [Pippin mobile](./pippin-storybook-mobile.png)

Desktop and 390px captures were inspected for Tamil clipping, facial proportions, control overlap, horizontal overflow, and readable scene changes.
