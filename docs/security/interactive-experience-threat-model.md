# Interactive Child Experience Threat Model

Date: 2026-08-01

## Scope and security objective

This review covers the Play & Practice web routes, the interactive-session API, parent roll-up, browser microphone/camera adapters, and their dependency surface. The primary objective is to make a child's practice private by default: the server receives only bounded aggregate counts, and every activity remains usable when microphone or camera access is declined.

## Trust boundaries and protected data

| Boundary | Untrusted input | Protection |
| --- | --- | --- |
| Browser to FastAPI | Activity IDs, timestamps, counts, durations, assistance totals | Authenticated route; Pydantic `extra="forbid"`; type, pattern, length, range, and consistency checks |
| Account ownership | Cookies/bearer token and any attempted client identity | User ID is derived only from `get_current_user`; `user_id` in a payload is rejected |
| Microphone | Live audio and Web Speech transcript | Used in memory; no raw audio or transcript field exists in the reporting model; tracks stop on exit/reset |
| Camera | Live video frames and face landmarks | Explicit caregiver gate; frames processed locally; report contains only aggregate turn counts; model-only fallback |
| Browser storage | Sensory and age-presentation preferences | Versioned allow-list migration; no token, transcript, audio, video, frame, or local Pippin history is persisted |
| Parent report | Aggregated child practice | Authenticated, per-user database query; no public ranking or cross-child endpoint |

## Abuse cases and controls

### Identity and cross-user access

- `POST /api/interactive-sessions` never accepts a user identifier. The authenticated database ID is inserted server-side.
- `GET /api/interactive-sessions/summary` filters on that same authenticated ID.
- Tests cover missing authentication, attempted `user_id` injection, and exclusion of another child's rows.

### Oversized or inconsistent input

- Activity IDs are restricted to 1-80 lowercase slug characters.
- Turns and successes are capped at 100, attempts at 300, duration at one hour, and effort at 10,000.
- Completion cannot precede start; successful turns and assistance totals cannot exceed communication turns.
- The summary query is limited to seven days and 500 rows, bounding database and aggregation work.

### Child media and transcript disclosure

- `audio`, `video`, `transcript`, and `frames` are forbidden extra fields and have regression tests.
- Pippin's exact words exist only in component memory and its five-item local history; server reporting uses counts only.
- Web Speech exact-repeat is disabled for River Rescue and Pippin so curated responses control what the companion says.
- A browser test starts a mocked microphone, exits the route, proves the track was stopped, and scans local storage for media/transcript keys.

### Camera interpretation risk

- Mouth Mirror measures only mouth width, mouth height, and opening ratio.
- The previous eyebrow-distance "stress" and "emotion" labels were removed. No attention, mood, engagement, diagnosis, or autism-severity claim is produced.
- Camera permission has an explicit caregiver-facing explanation and a model-only alternative.

### Script injection and unsafe rendering

- Child-recognized text is rendered through React text nodes; there is no `dangerouslySetInnerHTML`, `innerHTML` assignment, `eval`, `new Function`, or `document.write` in application source.
- Pippin strips URLs/control characters, caps unknown phrases to six words/80 characters, and redirects a small unsafe-word set to a kind-word prompt.
- React Router was upgraded from the client-XSS-affected 6.30.4 line to 7.18.2.

### Accessibility and sensory overload

- Controls have a 44 px minimum target, accessible names, keyboard reachability, and visible focus behavior.
- System reduced-motion preference is applied when no explicit saved choice exists.
- Calm mode forces minimal motion, disables celebrations and spoken prompts, and restores the prior settings when turned off.
- Stable visual schedules, pause/resume, skip/support paths, and microphone/camera fallbacks prevent a blocked failure state.

## Dependency and secret review

- Vite was upgraded to 8.2.0 and Vitest to 4.1.10, clearing the development-server path traversal and test-UI arbitrary file read advisories found during this audit.
- `python-jose` was raised to `>=3.4.0,<4` and `cryptography>=48.0.1` was made explicit to address the installed JWT/cryptography advisories.
- MediaPipe's jsDelivr URL is pinned to `0.4.1633559619` and sends no referrer. It is still a third-party runtime dependency.
- `.env` content was never printed or committed by this work. A staged deletion of `backend/.env` pre-existed this feature work and was intentionally left untouched.
- Targeted source scans found no unsafe HTML/eval API or token/transcript persistence. `model.eval()` in the Python speech service is the expected ML inference method, not JavaScript execution.

## Accepted residual risks

1. `npm audit --omit=dev` reports React Router's RSC/server-action CSRF advisory on 7.18.2. This project uses `BrowserRouter` as a static client SPA and exposes no React Server Components, loaders/actions, or React Router server runtime, so the vulnerable path is not reachable. Downgrading to 7.11 reintroduced multiple applicable client open-redirect/XSS advisories and was rejected.
2. MediaPipe code/model files load from pinned jsDelivr at runtime. A future production hardening pass should self-host these immutable files and add a restrictive Content Security Policy after validating all existing CDN/font/model consumers.
3. `pip-audit -r` could not resolve the legacy `mediapipe==0.10.11` pin on the workstation's Python 3.12 index. `pip-audit -l` covered the shared machine environment but includes many unrelated tools, so it is not a reliable project lock audit. Production dependencies should be compiled into a Python 3.11 hash-locked file inside the Docker build and audited there.
4. Browser speech recognition is vendor-provided and may process audio according to the browser vendor's policy. The UI does not claim that Web Speech inference itself is offline; only that SpeakEasy does not store the raw media.

## Verification evidence

- Backend: strict API and ownership tests plus the full Pytest suite.
- Frontend: pure session, preference, audio, quest, mouth geometry, Pippin, caregiver mission, and parent-summary tests.
- Browser: authenticated route mocks use a non-routable `.invalid` test identity; tests cover desktop/mobile overflow, large targets, keyboard focus, reduced motion, calm mode, pause/resume, media denial, model-only camera fallback, track teardown, and local-storage minimization.
