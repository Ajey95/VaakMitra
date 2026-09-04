# ASD-Edge-ST 2.0 — Backend Architecture (Member 3)

## Overview

This backend implements **Member 3** of the ASD-Edge-ST 2.0 system: session orchestration, adaptive dialogue engine, encrypted local database, privacy-safe metric synchronisation, and the Unity integration API.

---

## Processing Chain

```
Unity (C# HTTP Client)
        │
        ▼
┌─────────────────────────────────────────────────┐
│  FastAPI Local API  (asd_backend/main.py)       │
│  http://127.0.0.1:8765                          │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Session Orchestrator  (session/orchestrator.py) │
│  - Manages session state                        │
│  - Coordinates M1 and M2 pipeline               │
│  - Handles cancellation + timeout               │
│  - Persists structured metrics to DB            │
│  - Enqueues privacy-safe sync packets           │
└──────┬─────────────────────┬───────────────────┘
       │                     │
       ▼                     ▼
  Member 1              Member 2
  Audio Capture         Acoustic Model
  VAD + Alignment       CTC + GOP Scoring
  (interface stub)      (interface stub)
       │                     │
       └──────────┬──────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│  Adaptive Engine  (adaptive/engine.py)          │
│  - Pure rule-based logic                        │
│  - No ML, no clinical diagnosis                 │
│  - 7 decision branches                          │
│  - Full audit explanation per decision          │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Encrypted Local Database  (db/)                │
│  SQLite + SQLCipher                             │
│  10 entities, all pseudonymous                  │
│  No audio/embedding columns                     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼ (background, offline-safe)
┌─────────────────────────────────────────────────┐
│  Sync Service  (sync/service.py)                │
│  - Allow-list validated                         │
│  - Idempotency key per packet                   │
│  - TLS + bearer token auth                      │
│  - Exponential back-off                         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
        Therapist Server (remote)
        (or mock server in tests)
```

---

## Package Structure

```
asd_backend/
├── __init__.py          — package version
├── config.py            — env-driven settings (Settings)
├── main.py              — FastAPI app + lifespan
│
├── session/
│   ├── api.py           — M3.1: Unity-facing FastAPI router
│   ├── orchestrator.py  — M3.1: async session coordinator
│   ├── schemas.py       — typed request/response models
│   └── unity_contract.md— integration spec for Unity C#
│
├── adaptive/
│   ├── engine.py        — M3.2: rules-based decision engine
│   ├── policy.py        — TherapistPolicy Pydantic model
│   ├── schemas.py       — DecisionResult, ResponseIntent, etc.
│   └── scenarios/       — 10 YAML test scenario fixtures
│
├── db/
│   ├── models.py        — M3.3: 10 ORM entities + privacy guard
│   ├── database.py      — async engine + session factory
│   ├── repositories.py  — typed CRUD for all entities
│   └── encryption.py    — SQLCipher key derivation
│
└── sync/
    ├── allow_list.py    — M3.4: explicit allow-list + violation guard
    ├── service.py       — M3.4: background sync queue drain
    ├── therapist_api.py — M3.4: therapist-facing FastAPI router
    ├── schemas.py       — SyncPacket, TherapistReport, etc.
    └── mock_server.py   — in-process test server

config/
└── default_policy.json  — default therapist policy

tests/
├── conftest.py               — shared fixtures
├── test_adaptive_engine.py   — M3.5: 10+ scenario tests + privacy
├── test_db_privacy.py        — M3.5: schema privacy verification
├── test_sync_allow_list.py   — M3.5: packet inspection tests
├── test_session_orchestrator.py — M3.5: orchestrator lifecycle
├── test_recovery.py          — M3.5: cancellation + failure recovery
├── test_offline.py           — M3.5: airplane mode + queue drain
└── integration/
    └── test_full_pipeline.py — M3.5: end-to-end HTTP API tests
```

---

## Privacy Invariants

All seven invariants from §6.2 of the project specification are enforced here:

| # | Invariant | Enforcement |
|---|---|---|
| 1 | No child audio sent over network | `validate_sync_payload` + `test_sync_allow_list.py` |
| 2 | No embeddings/MFCC/phoneme-probs synced | Allow-list + blocked fragment check |
| 3 | Audio processed in RAM | `orchestrator.py`: audio held only in stack frame |
| 4 | Temp audio removed on cancel/fail/timeout | `orchestrator.py` finally block + `test_recovery.py` |
| 5 | Only pseudonymous min. metrics in sync queue | `build_sync_payload` + DB schema |
| 6 | Low confidence/invalid → no pronunciation judgement | `adaptive/engine.py` branches 2,3,4 + test |
| 7 | Result includes model/dict/policy versions | `Attempt` ORM columns + version fields in response |
| 8 | No ASD/not-ASD prediction | `adaptive/engine.py`: pure rule-based, no clinical output |

---

## Running the Backend

```powershell
# Install dependencies
cd c:\sem7\ASD
pip install -e ".[dev]"

# Copy env template
copy .env.example .env
# Edit .env — set ASD_DB_KEY to a strong secret

# Run development server
python -m asd_backend.main

# Or with uvicorn directly
uvicorn asd_backend.main:app --host 127.0.0.1 --port 8765 --reload
```

OpenAPI docs available at: `http://127.0.0.1:8765/docs`

---

## Running Tests

```powershell
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=asd_backend --cov-report=term-missing

# Privacy-critical tests only
pytest tests/test_sync_allow_list.py tests/test_db_privacy.py -v

# Integration tests
pytest tests/integration/ -v
```

---

## Member Interface Contracts

### Member 1 → Member 3 (AudioCaptureResult)
```python
AudioCaptureResult(
    attempt_id="ATT-00031",
    capture_status="valid",          # valid | silence | clipped | too_short | timeout
    expected_word="அம்மா",
    expected_phonemes=["a","m","m","a:"],
    phoneme_alignment=[...],         # list of {phoneme, start_ms, end_ms, confidence}
    alignment_confidence=0.85,
)
```

### Member 2 → Member 3 (ScoringResult)
```python
ScoringResult(
    attempt_id="ATT-00031",
    model_version="ta-phoneme-ctc-1.0.0",
    phoneme_scores=[...],            # list of PhonemeScoreInput
    syllable_scores=[...],           # list of SyllableScoreInput
    overall_confidence=0.84,
)
```

### Member 3 → Unity (AttemptResult JSON)
See [unity_contract.md](asd_backend/session/unity_contract.md).

---

## Sprint Checklist

| Sprint | Status | Deliverable |
|---|---|---|
| 1 — Skeleton | ✅ | Repo, DB schema, orchestrator skeleton, mock Unity API |
| 2 — Core | ✅ | Adaptive engine, DB repos, persistence |
| 3 — Edge | 🔲 | Sync allow-list, therapist endpoints, cancellation/recovery |
| 4 — Hardening | 🔲 | Security, packet inspection, full integration tests |
