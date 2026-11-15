# Adult Development Chunk Coach Implementation Plan

> **For agentic workers:** Execute inline in this task because the user requested no sub-agents or approval pauses. Every code task starts with a failing test.

**Goal:** Make the loopback adult lab demonstrate whole-word attempt → written chunk focus → blend → whole-word retry without claiming sound localization or child readiness.

**Architecture:** A pure backend helper produces transient written chunks and an optional ASR text-difference focus; the existing diagnostic endpoint includes this bounded hint. A small frontend state machine owns only the visual rehearsal cycle; `DiagnosticPanel` retains microphone and whole-word submission ownership.

**Tech Stack:** Python/FastAPI/Pytest; React/Vitest/Playwright; existing local adult diagnostic.

**Spec:** `docs/superpowers/specs/2026-09-15-adult-chunk-coach-design.md`.

## Constraints

- DEC-023/DCH-001..005: adult loopback only, no chunk score, no child/session write, no pronunciation diagnosis.
- DEC-003/008/022: canonical Tamil word and official `UNSCORABLE` remain authoritative.
- UX-002: no microphone while optional example speech plays.
- SES-006/PRV-002: no persisted transcript, candidate, or chunk hypothesis.

---

### Task 1: Transient visual chunk hint

**Files:** Create `backend/app/vaakmitra_word/dev_chunk_coach.py`; create `backend/tests/vaakmitra_word/test_dev_chunk_coach.py`.

**Interface:** `build_chunk_coach(target_word: str, candidate_word: str | None, *, capture_valid: bool) -> dict` returns status, target, chunks, nullable focus index/position, and basis.

- [x] Test Tamil reconstruction and focus for `அம்மா` versus `அப்பா`; RED before implementation.
- [x] Test identical/missing/non-Tamil candidate and invalid capture yield visual-only/no focus; RED.
- [x] Implement NFC Tamil cluster grouping, bounded chunk partition, and first text-difference mapping; GREEN.

### Task 2: Diagnostic response binding

**Files:** Modify `backend/app/vaakmitra_word/diagnostics.py` and `backend/tests/vaakmitra_word/test_diagnostics.py`.

**Interface:** existing `POST /api/dev/word-lab/assess` response gains `chunk_coach`; no other route changes.

- [x] Add failing route tests asserting no official decision promotion, ephemeral response, and candidate/quality fallback.
- [x] Call `build_chunk_coach` only after the existing bounded adult inference and return it in the diagnostic payload; GREEN.

### Task 3: Bounded visual rehearsal state

**Files:** Create `frontend/src/features/backendLab/chunkCoachFlow.js` and `chunkCoachFlow.test.js`.

**Interface:** `createChunkCoachFlow()` with `start(hint)`, `select(index)`, `advance()`, `reset()` and state `{phase, cycles, chunks, focusIndex}`; phases are `idle`, `focus`, `blend`, `whole_again`, `break`.

- [x] Test focus → blend → whole-again and second-cycle break cap; RED.
- [x] Test manual override, malformed hint fallback, target reset; RED.
- [x] Implement pure bounded flow; GREEN.

### Task 4: Adult lab UI and browser check

**Files:** Modify `frontend/src/features/backendLab/DiagnosticPanel.jsx`; add `frontend/tests/adult-chunk-coach.spec.js`.

**Interface:** after a real adult diagnostic response show the coach with visible unvalidated-hypothesis language and buttons to select/rehearse/blend/retry; optional `speechSynthesis` only with a local Tamil voice. The existing mic and WAV submit path remains the sole audio assessment path.

- [x] Add failing Playwright test for visible chunks, manual focus, coaching progression, whole-word resubmission only, reset/close, and no child route calls.
- [x] Implement the UI and prompt/mic cancellation invariants; make the browser test pass.
- [x] Run focused Python tests, frontend Vitest/ESLint/Vite/Playwright, full backend pytest, and a real adult loopback smoke. Record exact results and remaining limitations in `docs/VERIFICATION_STATUS.md` and `docs/BACKEND_COMPLETION_CONTEXT.md`; run `git diff --check`.
