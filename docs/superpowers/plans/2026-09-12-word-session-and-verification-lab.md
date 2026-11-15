# Word Session and Backend Verification Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Non-normative Phase 2 roadmap. The visual mockup was accepted, an isolated worktree was chosen, and Phase 1 audio admission and the development lab were implemented under `2026-09-12-backend-lab-phase1.md`. Do not execute the session-state tasks below until their authorization, concurrency, privacy, and rollback steps are expanded and self-reviewed against the SSOT. This roadmap does not authorize an Android architecture change to DEC-013.

**Goal:** Make the current private-edge word-session code path enforce its documented fail-closed boundaries and expose a development-only screen that tests real backend readiness and clearly labelled simulations.

**Architecture:** Preserve the existing FastAPI scorer and owned React app. Add server-owned therapist word assignments and session state around the scorer, then isolate the engineering lab behind a development-only route. Production scoring remains impossible until its externally approved bundle and child-validation gates are met.

**Tech Stack:** FastAPI, Pydantic, PyMongo asyncio, pytest, React/Vite, Axios, Vitest, Playwright.

**Spec:** `VAAKMITRA_FINAL_SSOT.md` (sole normative source), `docs/superpowers/specs/2026-09-12-backend-verification-lab-design.md` (diagnostic UI design).

## Global Constraints

- DEC-008/FUS-001..007: never fabricate PASS, a probability, or production readiness.
- DEC-013: the implementation target is the present private-edge backend; consumer-mobile deployment requires a separately approved SSOT revision.
- DEC-015/016: only a compatible approved bundle can score, and the versioned registry owns word identity and availability.
- AU-001/003: admit only locally decodable formats; cap request at 8 MiB and decoded duration at 0.30–12.0 seconds.
- UX-006/007, PRV-002..008: keep operator diagnostics away from child pages; do not persist audio, transcripts, candidates, embeddings, or probabilities.
- GATE-03..06 remain external release gates, even if all code-level tests pass.
- Preserve `D:\VaakMitra` and `D:\projects\omen\VaakMitra` unchanged.

## File map

- `backend/app/vaakmitra_word/router.py`: canonical assessment admission and session binding.
- `backend/app/vaakmitra_word/session_state.py`: domain-level plan/session authorization and retry transitions; no audio persistence.
- `backend/app/routers/therapist_ext.py`: therapist-owned word assignment data in existing treatment plans.
- `backend/app/database.py`: indexes for assigned sessions and unique attempts.
- `backend/app/config.py`: upload bound.
- `backend/tests/vaakmitra_word/test_api.py`, `test_session_state.py`: backend behavior tests.
- `frontend/src/features/backendLab/api.js`: health, registry, and assessment transport.
- `frontend/src/features/backendLab/fixtures.js`: simulation payloads with explicit provenance.
- `frontend/src/pages/BackendLabPage.jsx`, `BackendLabPage.css`: engineering-only screen.
- `frontend/src/App.jsx`, `frontend/vite.config.js`: dev-only route and health proxy.
- `frontend/src/features/backendLab/*.test.js`, `frontend/tests/backend-lab.spec.js`: logic and browser contract tests.

## Task 1: Fail-closed upload admission

**Requirements:** AU-001..004, FUS-001, DEC-008.

**Files:** Modify `backend/app/config.py`, `backend/app/vaakmitra_word/router.py`; test `backend/tests/vaakmitra_word/test_api.py`.

**Interfaces:** `bounded_audio(upload: UploadFile) -> bytes` keeps its signature. Canonical and legacy routes share it.

- [ ] **Step 1: Add a failing API test.** Assert a non-WAV WebM upload returns 415 before the service runs, and a WAV larger than 8 MiB returns 413 using an overridden limit. Test `service.contexts == []` in both cases. Name the test with AU-001/AU-003.
- [ ] **Step 2: Run red.** From `backend/`, run `python -m pytest tests/vaakmitra_word/test_api.py -q`; confirm the new assertions fail on the current permissive MIME/10 MiB behavior.
- [ ] **Step 3: Implement minimal admission.** Set `MAX_UPLOAD_BYTES = 8 * 1024 * 1024`; allow only PCM-WAV MIME variants and `application/octet-stream` pending WAV header validation. For octet-stream, reject bytes that do not begin with a RIFF/WAVE header. Preserve typed HTTP 415/413 errors. Do not add a decoder that is not installed.
- [ ] **Step 4: Run green.** Re-run the focused API tests and `python -m pytest tests/vaakmitra_word/test_audio.py -q` from `backend/`.
- [ ] **Step 5: Commit only Task 1 files.** `git add backend/app/config.py backend/app/vaakmitra_word/router.py backend/tests/vaakmitra_word/test_api.py`, then commit `fix: enforce supported word audio uploads`.

## Task 2: Bind word attempts to an assigned plan and owned session

**Requirements:** SSOT 13.1, DEC-016, DATA-012, PRV-002/005. Never use an untrusted client word as the authority.

**Files:** Create `backend/app/vaakmitra_word/session_state.py`, `backend/tests/vaakmitra_word/test_session_state.py`; modify `backend/app/routers/therapist_ext.py`, `backend/app/vaakmitra_word/router.py`, `backend/app/database.py`, `backend/app/main.py`; test `backend/tests/vaakmitra_word/test_api.py`.

**Interfaces:** `create_word_session(plan_id, user_id, db) -> SessionRecord`, `load_assigned_attempt(session_id, attempt_id, word_id, user_id, db) -> AttemptContext`, and `record_decision(context, result, db) -> None`. A therapist plan adds canonical `word_ids` and `vocabulary_version` fields. New session creation endpoint returns a pseudonymous session ID and the server-selected current word.

- [ ] **Step 1: Write failing domain tests.** Test that another user's session is rejected, a word outside the assigned plan is rejected, and reusing an `attempt_id` cannot produce a second transition. The expected result must come from literal plan/session fixtures, not from production helper output.
- [ ] **Step 2: Run red.** From `backend/`, run `python -m pytest tests/vaakmitra_word/test_session_state.py -q`; confirm missing domain APIs cause the failures.
- [ ] **Step 3: Implement the smallest domain layer.** Store only `owner_id`, `plan_id`, `vocabulary_version`, `word_ids`, current index, attempt count, stop/break state, and timestamps. Use Mongo conditional updates or a unique `(session_id, attempt_id)` index to make repeated submissions idempotent. Keep raw/normalized audio, ASR candidates, embeddings, DTW paths, and exact probabilities out of stored documents.
- [ ] **Step 4: Write failing route tests.** A therapist-assigned plan can start a session for its child; a user cannot start another child's plan; canonical assessment rejects a mismatched `word_id`/`target_word`/version before calling the scorer. Existing API tests must be updated to create a valid assigned session fixture, not bypass authorization globally.
- [ ] **Step 5: Implement route wiring.** Validate therapist-child ownership using the established `require_therapist` and assignment pattern. Add the session endpoint and require a bound session in canonical assessment. Leave the legacy endpoint explicitly compatibility-only; it must not be treated as clinical session evidence.
- [ ] **Step 6: Run green.** Run `python -m pytest tests/vaakmitra_word/test_session_state.py tests/vaakmitra_word/test_api.py -q` from `backend/` and confirm all pass.
- [ ] **Step 7: Commit only Task 2 files.** Commit `feat: bind word assessments to assigned sessions`.

## Task 3: Apply session retry/stop state without persisting forbidden evidence

**Requirements:** DEC-008, SSOT 14.1, UX-002/003, PRV-002..008.

**Files:** Modify `backend/app/vaakmitra_word/router.py`, `backend/app/vaakmitra_word/session_state.py`; test `backend/tests/vaakmitra_word/test_session_state.py`, `backend/tests/vaakmitra_word/test_api.py`.

**Interfaces:** The assessment context uses the session's real `attempt_count`, `stop_requested`, and `break_requested`. `record_decision` persists only allowed aggregate fields and the next safe session state.

- [ ] **Step 1: Write failing tests.** Three consecutive RETRY attempts cannot behave as three first attempts; a stop request yields `CALM_END/END`; a capability UNSCORABLE does not advance the word. Assert stored records contain no audio or exact probability.
- [ ] **Step 2: Run red.** Run the two focused pytest modules and confirm each new test fails because the route currently hardcodes `attempt_count=0` or lacks a transition.
- [ ] **Step 3: Implement transition handling.** Pass stored count/flags into `AssessmentContext`; update the session after the service returns using a conditional attempt record, and never advance on UNSCORABLE. Abort safely on duplicate/concurrent attempt IDs.
- [ ] **Step 4: Run green.** Re-run focused tests, policy tests, and privacy tests from `backend/`.
- [ ] **Step 5: Commit only Task 3 files.** Commit `feat: enforce governed word session transitions`.

## Task 4: Development-lab transport and simulation isolation

**Requirements:** Lab spec sections Screen/Data flow; DEC-008/015/016, UX-006, PRV-002..008.

**Files:** Create `frontend/src/features/backendLab/api.js`, `fixtures.js`, `api.test.js`, `fixtures.test.js`; modify `frontend/vite.config.js`.

**Interfaces:** `probeHealth(fetchImpl, signal) -> Promise<HealthRows>`, `loadVocabulary(fetchImpl, signal) -> Promise<Vocabulary>`, `submitAttempt(fetchImpl, {file, sessionId, attemptId, word, version, signal}) -> Promise<AssessmentResult>`, and `simulationFor(key) -> {source:'simulation', result}`. No simulation helper can call fetch.

- [ ] **Step 1: Write failing Vitest tests.** Fake only the network boundary and assert literal endpoint paths, cookie credentials, 8 MiB preflight, generic multipart filename, abort forwarding, 503 reason preservation, and simulation provenance.
- [ ] **Step 2: Run red.** From `frontend/`, run `npm test -- src/features/backendLab/api.test.js src/features/backendLab/fixtures.test.js`; confirm missing modules are the failure.
- [ ] **Step 3: Implement minimal transport and fixtures.** Probe `/health/live`, `/health/ready`, `/health/scoring`; use `/api/v1/vocabulary` and `/api/v1/word-assessments` for real calls. Proxy `/health` in Vite. Keep selected WAV and response in memory only; simulation fixtures carry `source: 'simulation'` and never enter the live result path.
- [ ] **Step 4: Run green.** Re-run focused Vitest tests and `npm run build`.
- [ ] **Step 5: Commit only Task 4 files.** Commit `feat: add isolated backend lab transport`.

## Task 5: Engineering-only UI and browser verification

**Requirements:** Lab spec Screen/Verification; DEC-002, UX-006/007, PRV-002..008.

**Files:** Create `frontend/src/pages/BackendLabPage.jsx`, `BackendLabPage.css`, `frontend/tests/backend-lab.spec.js`; modify `frontend/src/App.jsx`.

**Interfaces:** `/dev/backend-lab` exists only when `import.meta.env.DEV` is true. UI states are `idle`, `running`, `live-result`, `simulation`, `failed`, and `cancelled`; mode change clears the previous result.

- [ ] **Step 1: Write failing browser tests.** Verify the route renders `ENGINEERING ONLY`, `SIMULATED — NO BACKEND CALL` never calls the assessment endpoint, a live 503 remains visibly blocked, a 401 remains visible, and changing modes clears a simulated PASS. Use complete literal JSON fixtures at the network boundary.
- [ ] **Step 2: Run red.** Start the existing Vite dev server and run `npx playwright test tests/backend-lab.spec.js`; confirm the missing route is the reason for failure.
- [ ] **Step 3: Implement the screen.** Preserve the existing dashboard visual tokens without adding it to child navigation. Show separate health rows, authenticated vocabulary, an explicit adult/synthetic WAV upload, exact decision/reason/intent/state, and collapsible operator evidence. Provide cancel/clear controls. Never render a child-facing numeric accuracy, persist audio, or expose simulation as live.
- [ ] **Step 4: Run green and inspect.** Run focused Playwright, all Vitest tests, ESLint, and production build. Use a browser to inspect desktop and mobile-width rendering and exercise every control. Verify production output has no reachable lab route/component.
- [ ] **Step 5: Run backend regression.** From `backend/`, run `python -m pytest -q`. Record exact pass/fail counts and warnings, not a generic claim.
- [ ] **Step 6: Commit only Task 5 files.** Commit `feat: add development backend verification lab`.

## Completion and evidence boundary

Report live health, database, scoring readiness, auth, vocabulary, and adult/synthetic assessment separately. If bundle, MongoDB, consented canaries, child-separated calibration, or physical-device evidence is absent, mark it pending; no mock fixture or passing unit test may upgrade GATE-03..06. Any new mobile-on-device implementation begins only after DEC-013 change control.
