# Plan-backed word sessions — implementation slice

> Non-normative implementation plan. `VAAKMITRA_FINAL_SSOT.md` is the sole authority (Section 13.1, 14.1, DEC-008/016, DATA-012, PRV-002..008). No change to DEC-013 or consumer-mobile deployment is authorized by this plan.

**Goal:** Replace the canonical route's arbitrary client-selected `session_id`, word, version, and hardcoded retry count with a therapist-assigned, server-owned session and race-safe attempt transition. The legacy compatibility route remains explicitly non-clinical.

**Architecture:** A treatment plan stores versioned registry IDs; a session document stores owner/plan IDs, assigned IDs, current index, retry count, stop state, and an in-flight attempt claim. The canonical assessment claims its attempt before inference with an atomic conditional update; it releases/transitions only if the claim still belongs to it. No audio or model evidence is persisted. Completed attempt IDs live in the same session document: an atomic `$ne` predicate and `$addToSet` prevent duplicates without a second collection or cross-document transaction. Tests use literal in-memory repository fixtures and route overrides, never an invented score.

## Task A — plan and session authorization

1. Red tests: child ownership, therapist assignment, unassigned word, unsupported version, duplicate plan word, and missing plan return typed denial before scoring.
2. Add `word_ids` and `vocabulary_version` to therapist treatment-plan creation, validated against the server vocabulary. Legacy plans with no word assignment cannot start a word session.
3. Add `POST /api/v1/word-sessions` that reads the existing treatment plan from Mongo, checks owner or assigned therapist/admin, and creates a pseudonymous session with the first server-selected word. No client-supplied target is accepted. A partial unique index permits at most one active/paused session per plan; an existing open session or racing insert returns 409 rather than resetting the retry counter.
4. Green tests, then commit.

## Task B — atomic assessment claim and policy transition

1. Red tests: wrong owner/word/version, duplicate/concurrent `attempt_id`, retries escalating across attempts, capability `UNSCORABLE` not advancing, stop during inference suppressing a late PASS, and no forbidden audio/evidence in stored documents.
2. Canonical route loads and atomically claims the session before calling the scorer, passes server-owned `attempt_count`/constraints, then conditionally stores only decision/reason/next state. Stop endpoint wins over a pending inference and returns `CANCELLED` semantics. Database unavailable fails closed. The compatibility endpoint remains separate and clearly not session evidence.
3. Green focused and full backend suite; commit.

## Gate

No amount of session-state code can make an absent model bundle scoreable. Clinical calibration/child-separated validation, canaries, device tests, privacy/consent, and mobile DEC-013 change control remain outside this slice. Do not weaken the current dev lab to create a simulated session.
