# Backend Verification Lab design

**Status:** Written design for user review; not an implementation or release approval

**Authority:** `VAAKMITRA_FINAL_SSOT.md` v3.1.0 remains the sole normative source
**Scope:** DEC-002, DEC-008, DEC-012, DEC-013, DEC-015, DEC-016, UX-006..008, PRV-002..008, GATE-01..06

## Outcome and boundary

Add an operator-only, development-build screen that exercises the existing FastAPI word-assessment contract and reports the observed result. It is a diagnostic tool, not a child-facing therapy screen, clinical scorecard, production-readiness badge, or substitute for Android/Unity tests. It changes no scoring rule or release gate. The existing SSOT's DEC-013 private-GPU-edge architecture remains current; the proposed consumer-mobile architecture needs separate SSOT change control before implementation.

## Current evidence snapshot (2026-09-12)

- `/health/live` returned 200; `/health/scoring` returned 503 with `bundle_config_unavailable`; `/health/ready` did not finish within an eight-second diagnostic timeout. Unauthenticated `/api/v1/vocabulary` returned 401 as expected.
- The full backend pytest suite passed when run from `backend/`. That proves code-level checks, not a configured live deployment.
- `docs/VERIFICATION_STATUS.md` records adult engineering classifier, reference-bank, and calibration artifacts, but no approved production bundle, child-separated calibration, consented canaries, physical Android proof, or clinical sign-off.

The screen must display its own fresh observations rather than copying this dated evidence or inferring success from tests.

## Approaches considered

1. **Isolated development route in the owned React app — selected.** It reuses the API adapter and can run real browser-to-backend checks while leaving product navigation and child therapy paths unchanged (DEC-002, UX-007).
2. **Standalone static mock.** Good for visual review but cannot verify network, authentication, multipart upload, or real fail-closed responses. Retain only as an explicitly labelled simulation mode within the lab.
3. **Embed diagnostics in a therapy page.** Rejected because it mixes operator internals and numeric/technical evidence with child-facing UX (UX-006) and risks accidental production exposure.

## Screen and interaction

The `/dev/backend-lab` route is compiled/registered only for the local development build. It has a conspicuous `ENGINEERING ONLY` banner and is absent from production navigation/build output. It is for an authenticated adult/operator; it never asks a child to record or use the lab. The existing React routes and design remain intact (DEC-002, UX-007).

The screen contains four compact areas:

1. **Environment and health:** configured API origin, test time, HTTP status and latency for `/health/live`, `/health/ready`, and `/health/scoring`. Display precise backend reason codes and distinguish process alive, database ready, and scoring ready. A timeout is `UNKNOWN/TIMED OUT`, not PASS. The development proxy must explicitly route health calls; `/api` alone does not proxy `/health`.
2. **Authentication and vocabulary:** current operator authentication status; authenticated `GET /api/v1/vocabulary` with registry version and counts for intended/active/scoreable. A scoreable target is selectable for the normal assessment action. An unavailable target stays visibly unavailable; a separate, explicitly labelled `Test fail-closed response` action may select a server-listed intended target to verify abstention, never to imply it is scoreable. No local hardcoded target silently replaces the server registry (DEC-016).
3. **Real assessment:** an adult-consented or synthetic local WAV chosen deliberately by the operator, its local size/type, explicit upload action, and the exact authenticated multipart request to `POST /api/v1/word-assessments` (`audio`, `session_id`, `attempt_id`, `word_id`, `target_word`, `exercise_version`). No child recording or automatic microphone capture. Display HTTP status, exact `decision` (`PASS`, `RETRY`, `UNSCORABLE`), `reason_code`, `response_intent`, `avatar_state`, next exercise, latency, and artifact versions. A 401, 422, 503, timeout, or network error is shown as a failure/degraded state, never converted to PASS. Numeric probabilities, candidates, or raw evidence are restricted to a collapsible operator diagnostics area and never appear in a child-style success card (DEC-008, DEC-015, UX-006).
4. **Contract simulation:** labelled `SIMULATED — NO BACKEND CALL` across every simulated result. Fixed fixtures cover PASS, RETRY, invalid-capture UNSCORABLE, and missing-bundle UNSCORABLE. Simulation cannot set any live health badge or claim a model was exercised. It previews only the approved response-intent/avatar-state mapping; it does not render generated speech or assert Unity frame performance (DEC-012, UX-008).

Each mode has a distinct visual treatment and event source. Changing modes clears prior attempt results so a simulated PASS cannot be mistaken for live evidence. The real panel is never populated from fixture data. Stop/cancel aborts an in-flight request and discards the selected file reference.

## Data and privacy flow

Browser memory holds the selected local WAV only while the operator is using the lab. The file is sent solely to the configured private backend on explicit click; no third-party endpoint, analytics, localStorage, IndexedDB, or diagnostic log receives audio, transcript, candidates, embeddings, probabilities, or identifying filename. The UI may show a redacted basename locally but does not transmit it beyond the upload's required multipart metadata. No raw response body is persisted. Browser network and filesystem checks must verify these conditions (PRV-002..008).

The operator should use a synthetic or consented adult test file. The lab must reject a selected file over the configured upload limit before transport and must not present test fixtures as child validation. A browser upload necessarily transfers audio to FastAPI, so this lab is **not** evidence for the later fully on-device mobile architecture. The current private-edge trust boundary remains governed by DEC-013 and must be verified separately.

## Contract and implementation plan boundary

Prefer a small dedicated API adapter and UI components in `frontend/`, reusing the existing Axios cookie-auth behavior. Keep production bundles free of the dev route by build-time gating, not just a hidden link. Preserve the existing 401 redirect semantics in ordinary app pages; the lab should report a 401 meaningfully to its operator. Do not add a new backend scoring or simulation endpoint. The existing `GET /health/*`, `GET /api/v1/vocabulary`, and `POST /api/v1/word-assessments` are the only live lab calls. A local Vite proxy entry for `/health` may be needed.

This design does not assert that the legacy router collection (lessons, accounts, progress, therapist/parent, gamification, etc.) is end-to-end functional. Those are a separate inventory/test matrix, not automatically verified by a word-scoring lab.

## Verification and acceptance

- Unit/component tests prove fixture/live mode isolation, no fake live PASS, 401/422/503/timeout handling, vocabulary-disabled target behavior, exact request fields, cancellation, and approved response mapping (DEC-008, DEC-015, DEC-016, UX-006).
- A real local browser smoke run captures liveness, database readiness, scoring readiness, auth, vocabulary, and one explicitly authorized adult/synthetic upload. If no approved bundle is installed, expected evidence is `503` readiness and `UNSCORABLE` assessment, not an artificial success.
- Build the production frontend and verify the lab route/component is absent. Check network requests, browser storage, logs, and cleanup for forbidden audio/derived data (PRV-002..008, GATE-05).
- Run relevant frontend and backend suites. Report exact failures and the environment used. GATE-03 child-separated calibration, GATE-04 physical Android/Unity, GATE-05 packet evidence, and GATE-06 clinician approval remain separate release blockers.

## What breaks first

The first likely operational blocker is missing configuration: an unauthenticated or Mongo-unready backend cannot load the authenticated vocabulary, and the unapproved bundle cannot produce a score. The lab must make those independent failure causes obvious. The second is a dangerous evidence mix-up: a visually convincing simulated PASS could be read as a live result. The explicit mode separation and provenance labels are therefore acceptance criteria, not cosmetic details.
