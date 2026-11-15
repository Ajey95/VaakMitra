# Child Control and Report Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan inline. Steps use checkbox (`- [ ]`) syntax for tracking. The user prohibited subagents.

**Goal:** Make the child Break / Stop control safe and usable, replace inherited mock reports with real bounded session evidence, and provide a secure therapist handoff path.

**Architecture:** Keep server-owned session transitions and attempt records authoritative. The web client silences capture before requesting Pause; the server distinguishes voluntary breaks from retry/capability pauses. A separate report builder reads persisted events, generates denominated metrics, and exposes them only through the assigned-therapist authorization boundary. A later Android runtime must implement the same contracts locally without a cloud dependency during child practice.

**Tech Stack:** FastAPI/Pydantic/PyMongo, React/Vite/Vitest/Playwright, Android Kotlin/Compose, Python `cryptography` and WebAuthn-compatible passkey verification for signed review.

**Spec:** `docs/superpowers/specs/2026-09-14-child-control-therapist-handoff-design.md`

**2026-09-14 checkpoint:** Tasks 1–2 are implemented and pass unit/browser checks. Task 3 is partially implemented: a bounded persisted-session report projection and consent-gated list replace mock UI, but the canonical frozen version and richer support/schedule fields are not done. Task 4's request/independent-verification/withdrawal grant lifecycle is implemented; authenticated therapist remarks/passkey signature and immutable review are not. Task 5 is blocked by the absent on-device student and connected device; the inherited Android app still has a legacy audio-upload scorer and is not a consumer-edge release. The unchecked steps below remain a target checklist, not completed evidence. See `docs/VERIFICATION_STATUS.md` for current results.

## Global Constraints

- `VAAKMITRA_FINAL_SSOT.md` v3.3.0 is normative; cite DEC-020/021, SES-004/007/008, UX-003/009, PRV-011, RPT-001..007 in changed tests and code.
- No camera permission, attention score, phoneme localization, mock clinical score, or unrestricted dialogue.
- A missing model/artifact/calibration or uncertain capture never becomes PASS; signed review never becomes automated clinician approval.
- Preserve `D:\VaakMitra`, `D:\projects\omen\VaakMitra`, and unrelated changes in the original checkout.

---

### Task 1: Voluntary break server transition

**Files:** Modify `backend/app/vaakmitra_word/session_state.py`; test `backend/tests/vaakmitra_word/test_session_state.py`.

**Interfaces:** `WordSessionStore.pause(session_id, actor)` persists `pause_reason=user_pause` and timestamp; `WordSessionStore.resume(session_id, actor, next_word_id=None)` permits same-owner resume only for `user_pause` after `SessionLimits.break_seconds`, still enforcing current plan and lifetime. Retry/capability resumes remain adult-only.

- [ ] Add a failing test: owner pause then resume before break raises `completed_break_required`; after moving the injected clock beyond the break, same-word resume succeeds without resetting attempts.
- [ ] Run `python -m pytest backend/tests/vaakmitra_word/test_session_state.py -q` from the repository root and confirm that the test fails for the missing owner-resume branch.
- [ ] Add a failing test: owner cannot resume a retry-limit or capability pause, and a revoked plan cannot resume.
- [ ] Implement the narrow owner-resume branch; retain the existing adult branch and atomic status/index guard.
- [ ] Re-run the targeted test file; then run `python -m pytest backend/tests/vaakmitra_word/test_word_sessions.py backend/tests/vaakmitra_word/test_session_state.py -q`.

### Task 2: One-touch red child control

**Files:** Modify `frontend/src/components/therapy/SlideManager.jsx`, `frontend/src/pages/TherapyPage.jsx`, and `frontend/src/features/wordSession/sessionFlow.js`; test `frontend/src/features/wordSession/sessionFlow.test.js` and `frontend/tests/word-session.spec.js`.

**Interfaces:** First `Break / Stop` activation calls the current `flow.pause()` path, which aborts the assessment request and makes `Slide3_Evaluation` discard capture when phase leaves `active`; after Pause confirms, a choice sheet shows `Take a break` and `End session`. `End session` calls `flow.stop()`; a voluntary break shows a disabled Continue control until the server allows resume. A pause error cannot leave the microphone active.

- [ ] Add a failing unit test for an in-flight assessment canceled by the red control's pause transition; add a Playwright test that presses the button while recording and verifies the media track ends before the choice appears.
- [ ] Run `npm test -- --run src/features/wordSession/sessionFlow.test.js` and targeted Playwright in `frontend`; observe the expected failures.
- [ ] Implement the red control and accessible choice sheet without changing unrelated inherited routes or lesson layouts.
- [ ] Re-run unit and Playwright tests; inspect 390px viewport overflow and keyboard focus order.

### Task 3: Real session report and empty state

**Files:** Create `backend/app/vaakmitra_word/session_report.py`; modify `backend/app/vaakmitra_word/router.py`, `frontend/src/pages/ReportsPage.jsx`; test `backend/tests/vaakmitra_word/test_session_report.py` and `frontend/tests/page-functionality.spec.js`.

**Interfaces:** `GET /api/v1/word-sessions/{session_id}/report` returns a frozen versioned document derived from persisted events with session/word counts and explicit unavailable fields; never exposes audio/transcript/embeddings/exact confidence. The Reports page reads this document or displays `No verified word-session report yet` without mock percentages, camera time, or phoneme charts.

- [ ] Write failing report-builder tests with literal event fixtures for first-attempt PASS, supported eventual PASS, RETRY, UNSCORABLE, and canceled capture; assert denominators and absence of forbidden fields.
- [ ] Run targeted pytest; confirm missing implementation failure.
- [ ] Implement report builder and current-assignment read authorization, then re-run targeted and router tests.
- [ ] Write failing browser test for a no-report account; assert that mock values such as `87%`, peer ranks, and camera time are absent.
- [ ] Replace the mock report surface with authenticated report/empty/error views; run frontend tests and production build.

### Task 4: Authenticated therapist review

**Files:** Create `backend/app/vaakmitra_word/report_review.py`, `backend/app/routers/word_report_reviews.py`; modify `backend/app/database.py`, `backend/app/main.py`; test `backend/tests/vaakmitra_word/test_report_review.py`.

**Interfaces:** A server-issued nonce is bound to report digest plus therapist remarks/plan digests. Registration stores only public credential material. Review submission verifies a passkey assertion, current therapist assignment, consent, freshness, replay prevention, and immutable report version before appending a signed review receipt. No shared HMAC or typed reviewer name is accepted as therapist signature.

- [ ] Write failing tests for valid verification and separate failures for changed report bytes, altered remarks, replayed nonce, former therapist, absent consent, and no credential.
- [ ] Run targeted pytest and confirm each failure is the missing review behavior.
- [ ] Implement strict Pydantic request schemas, cryptographic verification, append-only storage and audited endpoints, then run the targeted tests.
- [ ] Run all backend security and word-session suites; inspect exported receipt for private-key/audio leakage.

### Task 5: Android parity and release evidence

**Files:** Modify the appropriate `SpeakEasyAndroid/app/src/main/java/com/team96/speakeasy/ui/screens/PracticeScreen.kt` and data/runtime modules after an Android code audit; add `SpeakEasyAndroid/app/src/androidTest/` instrumentation tests; update `docs/VERIFICATION_STATUS.md`.

**Interfaces:** Android child sessions use local on-device VAD/student/classifier/reference/calibration and the same Break / Stop, report, and avatar-state contracts. Android Keystore signs local report snapshots. Missing student artifacts return UNSCORABLE and do not fall back to a cloud scorer.

- [ ] Audit the Android runtime and artifact availability on a representative Android 10+ ARM64, 4 GB device and record exact APK, model-bundle, and device hashes.
- [ ] Write failing instrumentation tests for first-touch microphone cancellation, offline practice, report persistence/signing, and fail-closed missing artifacts.
- [ ] Implement the tested native paths without adding a child-session cloud dependency; run connected-device tests plus cold/warm latency, RAM, battery, thermal, packet-capture, and decision-parity checks.
- [ ] Update the verification ledger with measured results and leave release gates open wherever qualified child validation or clinical evidence is missing.
