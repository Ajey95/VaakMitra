# Governed Review and Checkups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan inline. Steps use checkbox (`- [ ]`) syntax for tracking. The user prohibited subagents.

**Goal:** Deliver operational, fail-closed human-evidence workflows and an every-14-day caregiver-booked therapist checkup without fabricated approval.

**Architecture:** FastAPI/Mongo stores authenticated metadata and audit transitions; local CLI builds hash-bound review exports for existing artifact builders. The current React appointments/therapist screens consume real API state. Clinical/scoring release gates remain external and false until real evidence exists.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, async PyMongo, pytest; React 18/Vite, Vitest/Playwright.

**Spec:** `docs/superpowers/specs/2026-09-14-governed-review-checkups-design.md`

## Global Constraints

- Follow SSOT v3.2.4 DEC-019, GOV-001..007, CHK-001..004, DATA-002/006/008/012/013, GATE-03/06, PRV-001..009, UX-007.
- Preserve `D:\VaakMitra` and `D:\projects\omen\VaakMitra`; edit only the clean Lab worktree.
- No child audio/documents in Mongo, repository, API exports, or outbound notifications.
- No fake reviewer, consent, clinician, appointment, metric, score, or PASS state.
- All human credentials, consent, reference, canary, and clinical decisions default pending; scoring does not unlock from UI status alone.

---

### Task 1: Adult-reference provenance gate

**Files:** Modify `backend/scripts/model/build_reference_bank.py`; create `backend/tests/vaakmitra_word/test_reference_approval_manifest.py`.

**Interfaces:** `validate_approval_manifest(payload: dict, source_records: dict[str, CorpusRecord], source_hash: str) -> dict[str, dict]`; consumed by CLI `main()`.

- [ ] Write a failing test with a source record (`sample_id`, word, audio hash) and `human_approved=False`; assert `RuntimeError("approval_manifest_human_review_required")`.
- [ ] Run `python -m pytest tests/vaakmitra_word/test_reference_approval_manifest.py -q` from `backend`; confirm RED.
- [ ] Implement exact SHA/source/word/sample, reviewer/provenance/quality/capture checks; reject duplicate approvals and unmatched approved rows before loading embeddings.
- [ ] Run focused tests and the CLI help test; confirm GREEN, then commit scoped files.

### Task 2: Credential and consent metadata workflow

**Files:** Create `backend/app/routers/governance.py`; modify `backend/app/main.py`, `backend/app/database.py`; create `backend/tests/test_governance.py`.

**Interfaces:** `GET /api/governance/overview`; `POST /api/governance/credentials`; `POST /api/governance/consents`; `POST /api/governance/consents/{id}/verify`; authenticated server actor controls state, not client reviewer fields.

- [ ] Write failing async route tests: self-credential rejection, non-admin verification rejection, consent remains pending after caregiver submission, verified consent requires distinct admin and future-effective scope.
- [ ] Run `python -m pytest tests/test_governance.py -q`; confirm RED.
- [ ] Add Pydantic input models with `extra=forbid`, exact SHA-256 validation, scoped status records, immutable append-only review events, indexes, and audit calls.
- [ ] Run focused tests and backend suite; confirm GREEN, then commit scoped files.

### Task 3: Adult reference, canary, clinical review and export

**Files:** Extend `backend/app/routers/governance.py`; create `backend/app/vaakmitra_word/review_exports.py`; extend `backend/tests/test_governance.py`; modify `backend/app/vaakmitra_word/canary.py` and its tests if needed.

**Interfaces:** `POST /api/governance/reviews`, `GET /api/governance/reviews`, `GET /api/governance/references/export`; `export_reference_approvals(source_hash, source_records, decisions) -> dict`; exact hashes and qualified actor required.

- [ ] Write failing tests for unqualified signer, changed source/audio/word hash, duplicate decision, clinical bundle change, canary suite category/word coverage and source leakage.
- [ ] Run focused tests; confirm RED.
- [ ] Implement minimal metadata-only review transitions and export; require server identity, scoped verified credential, distinct human provenance, exact manifest binding, and append-only audit. Candidate review never sets clinical gate itself.
- [ ] Run focused tests and backend suite; confirm GREEN, then commit scoped files.

### Task 4: Checkup clock and appointment authorization

**Files:** Create `backend/app/vaakmitra_word/checkups.py`, `backend/tests/test_checkups.py`; modify `backend/app/routers/appointments.py`, `backend/app/routers/therapist.py`, `backend/app/database.py`; create `backend/tests/test_appointments_checkups.py`.

**Interfaces:** `checkup_status(assigned_at, completions, appointments, at) -> dict`; `GET /api/appointments/checkup-status`; `POST /api/appointments/checkups`; `PATCH /api/appointments/{id}/status` checks actor + transition + relationship.

- [ ] Write failing pure clock tests for 14-day boundary, no assignment timestamp, pending/cancelled/no-show not resetting, completed checkup reset.
- [ ] Run focused tests; confirm RED; implement pure clock, rerun GREEN.
- [ ] Write failing route tests for unauthorized completion, stale relationship, duplicate open request, past completion, and ordinary appointment not resetting checkup; confirm RED.
- [ ] Implement conditional updates, assignment timestamp and slot/open-request indexes; run focused/backend suites, then commit scoped files.

### Task 5: Real caregiver and therapist screens

**Files:** Modify `frontend/src/pages/AppointmentsPage.jsx`, `frontend/src/pages/ParentDashboard.jsx`, `frontend/src/pages/TherapistDashboard.jsx`, `frontend/src/services/api.js`; create focused Vitest files.

**Interfaces:** `appointmentsAPI.checkupStatus()`, `appointmentsAPI.bookCheckup(payload)`, existing `appointmentsAPI.list/therapists/reschedule/cancel`; governance review API from Task 3.

- [ ] Write failing rendered/component tests for real API empty state, due reminder, booking state change, no fictional doctors, and therapist-only review action.
- [ ] Run `npm test -- --run <focused files>` from `frontend`; confirm RED.
- [ ] Replace hardcoded appointment data with authenticated API data and accessible loading/error/empty states; wire a minimal therapist review screen without changing the owned layout.
- [ ] Run focused/frontend suites, lint, build, then rendered desktop/mobile interaction QA; confirm GREEN and commit scoped files.

### Task 6: End-to-end evidence and release ledger

**Files:** Update `docs/VALIDATION_HANDOFF.md`; create `docs/GOVERNANCE_REVIEW_HANDOFF.md`; add a focused Mongo integration test under `backend/tests`.

**Interfaces:** Demonstrate pending consent/qualification/review, successful real actor transitions, export compatible with reference builder, and checkup booking/completion/due reset.

- [ ] Write the integration test against a disposable database and run it RED if a path is absent.
- [ ] Complete any missing links; run backend suite, frontend tests/lint/build, real Mongo flow, CLI help, and browser QA.
- [ ] Record exact evidence and all human/child/device gates still pending. Do not claim 100% clinical or mobile readiness from engineering tests.
- [ ] Review `git diff --check` and final status; commit scoped docs/tests only after fresh verification.
