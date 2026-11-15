# Backend Lab Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce the current scorer's actual audio admission contract and build a dev-only UI that distinguishes live backend checks from simulated contract states.

**Architecture:** Keep the existing FastAPI routes and owned React app. Restrict uploads to PCM WAV until another decoder is installed, and place a standalone operator lab behind a development-only route, with pure transport/fixture helpers and no persistent audio.

**Tech Stack:** FastAPI, pytest, React 18, Vite 8, Vitest 4, Playwright.

**Spec:** `VAAKMITRA_FINAL_SSOT.md` (DEC-002/008/013/015/016, AU-001/003, UX-006/007, PRV-002..008) and `docs/superpowers/specs/2026-09-12-backend-verification-lab-design.md`.

## Global Constraints

- `PASS`, `RETRY`, `UNSCORABLE` are the only decisions. No fake score, production readiness, or child-facing percentage.
- Current private-edge FastAPI is the target. Android on-device inference requires DEC-013 change control and is outside this slice.
- The diagnostic lab is build-time excluded from production and is never linked in child navigation.
- Only operator-selected adult-consented/synthetic PCM WAV may be sent; no audio, transcript, candidates, embeddings, or probabilities are persisted by the lab.
- Missing MongoDB/auth/bundle remains visible as a failure or `UNSCORABLE`; simulations never alter live status.

## File map

- `backend/app/config.py`, `backend/app/vaakmitra_word/router.py`: enforce upload-size and decoder admission.
- `backend/tests/vaakmitra_word/test_api.py`: real FastAPI boundary regression.
- `frontend/src/features/backendLab/labClient.js`: fetch-based, cookie-auth live probes and upload.
- `frontend/src/features/backendLab/fixtures.js`: deterministic simulation results with provenance.
- `frontend/src/features/backendLab/labClient.test.js`, `fixtures.test.js`: live/sim separation.
- `frontend/src/pages/BackendLabPage.jsx`, `BackendLabPage.css`: screen and states.
- `frontend/src/App.jsx`, `frontend/vite.config.js`: development-only route and `/health` proxy.
- `frontend/tests/backend-lab.spec.js`: browser behavior.

---

### Task 1: Admit only currently decodable audio

**Files:** Modify `backend/app/config.py`, `backend/app/vaakmitra_word/router.py`; test `backend/tests/vaakmitra_word/test_api.py`.

**Interfaces:** `bounded_audio(upload: UploadFile) -> bytes` remains the shared admission function for canonical and compatibility endpoints.

- [ ] **Step 1: Write the failing tests.** Extend the existing `client()`/`FakeService` fixture with these consumer-visible assertions (AU-001/003):

```python
def test_au001_webm_is_rejected_before_scoring():
    api, service = client()
    response = api.post('/api/v1/word-assessments', data={
        'session_id': 'SES-1', 'attempt_id': 'ATT-1', 'word_id': 'TA_00021',
        'target_word': 'அம்மா', 'exercise_version': 'ta-core-1.0.0',
    }, files={'audio': ('sample.webm', b'\x1aE\xdf\xa3', 'audio/webm')})
    assert response.status_code == 415
    assert service.contexts == []

def test_au003_wav_larger_than_eight_mib_is_rejected():
    api, service = client()
    response = api.post('/api/v1/word-assessments', data={
        'session_id': 'SES-1', 'attempt_id': 'ATT-1', 'word_id': 'TA_00021',
        'target_word': 'அம்மா', 'exercise_version': 'ta-core-1.0.0',
    }, files={'audio': ('sample.wav', b'RIFF' + b'X' * (8 * 1024 * 1024), 'audio/wav')})
    assert response.status_code == 413
    assert service.contexts == []
```

- [ ] **Step 2: Run red.** From `backend/`, `python -m pytest tests/vaakmitra_word/test_api.py -q`; expect 415/413 assertions to fail on current behavior.
- [ ] **Step 3: Implement the minimal change.** Set `MAX_UPLOAD_BYTES` to `8 * 1024 * 1024`. In `bounded_audio`, reject unsupported MIME before read, and reject non-`RIFF....WAVE` headers with HTTP 415 after bounded read. Keep octet-stream for real WAV files only. Do not decode WebM without a local installed decoder. Replace the four existing `b"RIFF"` FakeService test fixtures in `test_api.py` with a minimal `b"RIFF\x04\x00\x00\x00WAVE"` header so they still exercise their intended behavior rather than the new upload guard.

```python
if data[:4] != b'RIFF' or data[8:12] != b'WAVE':
    raise HTTPException(status_code=415, detail='unsupported_audio_type')
```

- [ ] **Step 4: Run green.** From `backend/`, `python -m pytest tests/vaakmitra_word/test_api.py tests/vaakmitra_word/test_audio.py -q`.
- [ ] **Step 5: Commit only Task 1 files.** `git add backend/app/config.py backend/app/vaakmitra_word/router.py backend/tests/vaakmitra_word/test_api.py`; `git commit -m "fix: enforce decodable word uploads"`.

### Task 2: Isolate live transport from simulation

**Files:** Create `frontend/src/features/backendLab/labClient.js`, `fixtures.js`, `labClient.test.js`, `fixtures.test.js`; modify `frontend/vite.config.js`.

**Interfaces:** `probeHealth(fetchImpl, signal)`, `loadVocabulary(fetchImpl, signal)`, `submitAttempt(fetchImpl, input)`, `simulationFor(key)`. Live responses have `source: 'live'`; fixtures have `source: 'simulation'`.

- [ ] **Step 1: Write failing tests.** Use a fake fetch that returns literal `Response` objects. Assert `GET /health/scoring` preserves 503 plus `bundle_config_unavailable`, vocabulary sends `credentials: 'include'`, a too-large WAV is rejected before any call, and a simulation never invokes fetch (DEC-008/015/016, PRV-002):

```javascript
import { expect, it } from 'vitest'
import { probeHealth, submitAttempt } from './labClient'
import { simulationFor } from './fixtures'

it('dec008 preserves the live scoring blocker', async () => {
  const fetcher = async () => new Response(JSON.stringify({detail:{ready:false,reasons:['bundle_config_unavailable']}}), {status:503,headers:{'Content-Type':'application/json'}})
  const rows = await probeHealth(fetcher)
  expect(rows.scoring).toMatchObject({ source:'live', status:503, reasons:['bundle_config_unavailable'] })
})

it('prv002 rejects an oversized local file without transport', async () => {
  let called = false
  const file = new File([new Uint8Array(8 * 1024 * 1024 + 1)], 'adult.wav', {type:'audio/wav'})
  await expect(submitAttempt(() => { called = true }, {file})).rejects.toThrow('audio_too_large')
  expect(called).toBe(false)
})

it('dec008 labels local fixtures as simulation', () => {
  expect(simulationFor('capability')).toMatchObject({source:'simulation', result:{decision:'UNSCORABLE', reason_code:'MODEL_UNAVAILABLE'}})
})
```

- [ ] **Step 2: Run red.** From `frontend/`, run `node_modules/.bin/vitest run src/features/backendLab/labClient.test.js src/features/backendLab/fixtures.test.js` with the supported Node 24 executable; expect missing modules.
- [ ] **Step 3: Implement.** `probeHealth` calls all three health endpoints with an eight-second abortable timeout per request, preserving numeric status, reason codes, and `source:'live'`. `loadVocabulary` uses `/api/v1/vocabulary`. `submitAttempt` validates `.wav`, 8 MiB, required server-listed word metadata, then posts a `FormData` with a generic `attempt.wav` filename, `credentials:'include'`, and caller signal. `simulationFor` returns fixed result objects without a network dependency. Add Vite `/health` proxy to localhost port 8000.

```javascript
const form = new FormData()
form.append('audio', file, 'attempt.wav')
for (const [key, value] of Object.entries(fields)) form.append(key, value)
return fetchImpl('/api/v1/word-assessments', {method:'POST', credentials:'include', body:form, signal})
```

- [ ] **Step 4: Run green.** Run focused Vitest and production build with Node 24.
- [ ] **Step 5: Commit only Task 2 files.** `git add frontend/src/features/backendLab frontend/vite.config.js`; `git commit -m "feat: add backend lab transport and fixtures"`.

### Task 3: Render the engineering-only lab

**Files:** Create `frontend/src/pages/BackendLabPage.jsx`, `BackendLabPage.css`, `frontend/tests/backend-lab.spec.js`; modify `frontend/src/App.jsx`.

**Interfaces:** `/dev/backend-lab` exists only when `import.meta.env.DEV`. The page consumes Task 2 helpers and never routes simulated results into the live panel.

- [ ] **Step 1: Write failing Playwright tests.** Mock `/api/auth/me` as 401, `/health/live` as 200, `/health/ready` as a timed-out request, `/health/scoring` as 503, and `/api/v1/vocabulary` as 401; navigate to `/dev/backend-lab`. Assert the banner and exact blocker. Select the capability fixture, assert `SIMULATED — NO BACKEND CALL` and `UNSCORABLE`, and assert zero `/api/v1/word-assessments` calls. Changing mode clears the old result (DEC-008, UX-006).
- [ ] **Step 2: Run red.** Start Vite and run `npx playwright test tests/backend-lab.spec.js`; expect missing-route failure.
- [ ] **Step 3: Implement.** Follow `docs/mockups/backend-lab-concept.png`: white/indigo/cyan, four sequential live sections and clearly separated hatched simulation panel. Put `ENGINEERING ONLY` above the title. Use semantic buttons/select/label and mobile-safe stacking. Do not add to child navigation; gate the lazy import and route by `import.meta.env.DEV`.

```jsx
{import.meta.env.DEV && <Route path="/dev/backend-lab" element={<BackendLabPage />} />}
```

- [ ] **Step 4: Run green and verify.** Run focused Playwright, all Vitest, ESLint, and `npm run build` with Node 24; inspect desktop and mobile in Browser/IAB, compare to concept via `view_image`, and verify the production output excludes the lab. From `backend/`, run `python -m pytest -q`.
- [ ] **Step 5: Commit only Task 3 files.** `git add frontend/src/pages/BackendLabPage.jsx frontend/src/pages/BackendLabPage.css frontend/src/App.jsx frontend/tests/backend-lab.spec.js docs/mockups/backend-lab-concept.png`; `git commit -m "feat: add development backend verification lab"`.

## Completion boundary

Report observed live health/auth/vocabulary/assessment separately. This phase does not implement plan-backed retries, VAD ONNX, approved calibration, child validation, Android on-device inference, or clinical readiness; those remain in the separately tracked backend roadmap. A test fixture cannot unlock a release gate.
