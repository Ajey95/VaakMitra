# Scoring evidence and guarded therapy UI Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for the independent UI task and reviewed inline work for the shared scoring pipeline. Preserve the existing uncommitted backend-lab work.

**Goal:** Rebuild reproducible live-pipeline adult calibration evidence, audit complete vocabulary/reference coverage, execute only authorized validation, and connect the inherited therapy UI to guarded sessions.

**Architecture:** Reuse WordAssessmentService.assess and EvidenceCalibrator.features as the only acoustic/feature path. Produce immutable adult engineering outputs in a new dated directory, never promote approvals. The therapy UI consumes server-owned session targets and decisions, not legacy lesson IDs or local attempt counters.

**Tech Stack:** Python, NeMo, NumPy, scikit-learn, ONNX VAD, FastAPI/MongoDB, React/Vitest/Playwright.

**Spec:** VAAKMITRA_FINAL_SSOT.md v3.2.1.

## Global Constraints

- No step may bypass the readiness or abstention behavior to make a demo appear successful.
- DATA-002: Target validation uses ethics-approved, guardian-consented, age-appropriate recordings and therapist labels.
- DATA-004: Final test children are excluded from model training, classifier training, threshold selection, normalization tuning, and reference selection.
- DATA-006: At least two qualified raters label validation data; disagreements are adjudicated and inter-rater agreement is reported.
- UX-007: Preserve the owned React frontend's routes, layout, and visual design. Change only data adapters and misleading/safety-critical copy needed for this contract.
- Protected D:\VaakMitra and D:\projects\omen\VaakMitra remain read-only. Do not change human approval fields or claim AI labels are human evidence.

### Task 1: Guarded inherited therapy UI

**Files:** frontend/src/components/therapy/Slide3_Evaluation.jsx, SlideManager.jsx; frontend/src/pages/TherapySession.jsx or its existing equivalent; frontend/src/services/api.js and focused session adapter/hook and tests as needed. Backend contracts are read-only for this task.

**Interfaces:** Consume POST /api/v1/word-sessions {plan_id}, GET /api/v1/word-sessions/{id}, POST /api/v1/word-assessments multipart {audio, session_id, attempt_id, word_id, target_word, exercise_version}, POST pause/stop/resume and GET summary. Plan selection must use existing authenticated assigned-plan API, never synthesize plans or child identity. Produce canonical server-controlled therapy lifecycle without legacy /api/evaluate/speech calls.

- [ ] Write failing behavioral tests for missing plan blocking capture, canonical multipart target/version from server snapshot, no legacy endpoint, pause/stop aborting capture and suppressing late result, no local-count advancement, and neutral UNSCORABLE rendering.
- [ ] Run focused Vitest tests to prove RED, then implement the minimal adapter/hook and wire the existing visual components. Keep server session IDs ephemeral; no audio/transcripts in storage. Request UUID remains stable for a submitted capture; prevent duplicate submit.
- [ ] Use server snapshot after assessment to determine current word/paused/ended state. Do not advance on arbitrary lesson navigation or allow the child to invoke adult-only resume. Missing/retired plans and missing capability remain explicit safe blocked states. Remove automatic browser TTS from this scoring flow; approved local prompts only.
- [ ] Run focused tests, full frontend unit tests, lint/build and one-worker browser checks. Exercise actual rendered plan/session flow using labeled synthetic API responses; record desktop/mobile screenshots outside repo. Do not claim approved model scoring from synthetic responses.
- [ ] Self-review and commit only this task's files; write report with RED/GREEN commands and remaining risks.

### Task 2: Exact live feature evidence and artifacts

**Files:** backend/app/vaakmitra_word/calibration.py, calibration_training.py; backend/scripts/model/calibrate_engineering.py; new backend/app/vaakmitra_word/live_evidence.py and backend/scripts/model/rebuild_live_evidence.py; corresponding tests.

**Interfaces:** assess(audio_bytes, AssessmentContext) -> AssessmentResult; EvidenceCalibrator.features(evidence, quality) -> dict. Persist only authorized adult research-build features, not product session data. Bind model/classifier/bank/vocabulary/VAD and live code pipeline hashes to output.

- [ ] Inventory approved/machine-reviewed manifests and existing embedding provenance. Audit all 100 canonical words, distinct speakers, counts, held-out splits, OTHER examples and review status. Report deficits explicitly; never silently shrink the registry or duplicate samples to reach targets.
- [ ] Write failing tests for shared live feature parity, model/VAD mismatch, same-speaker leakage, changed source checksum, and missing human-review evidence. Reuse the live service directly rather than a second DTW/quality implementation.
- [ ] Implement deterministic bounded manifest-driven evidence extraction, matched and wrong targets, immutable JSONL output, source checksums, code/config provenance, and separate calibration/evaluation speakers. Reject child rows in adult training. Add CLI VAD/pipeline binding to calibration output.
- [ ] Run the real adult extraction and fit to a new output directory, preserving the old artifacts. Run holdout engineering metrics and report actual coverage/failed gates, never clinical approval.

### Task 3: Validation and canary readiness

**Files:** existing canary/governance modules and scripts, new audit/evaluation helpers and tests only where missing; docs/BACKEND_COMPLETION_CONTEXT.md and docs/BACKEND_LAB_HANDOFF.md.

**Interfaces:** Read existing owned/eval labels and governance evidence locally. Outputs contain pseudonyms, counts, checksums and readiness reasons; no raw child audio/transcripts in committed files.

- [ ] Audit consent, ethics, distinct child groups, two raters, adjudication and split independence before any child inference. One child cannot populate separate child calibration and final-test partitions.
- [ ] Add executable fail-closed validation/preflight checks where absent; test missing consent, duplicated child across splits, AI-only labels and unsigned canary expectations.
- [ ] Run approved available canaries, or produce an explicitly unapproved candidate/readiness manifest without fabricated sign-off. Stop only the unauthorized child evaluation step while continuing the independent software tasks.
- [ ] Verify combined backend/frontend tests, exact adult pipeline, guarded UI and final diff; document completion versus human/data blockers with exact outputs.
