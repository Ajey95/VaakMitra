# VaakMitra Word-Level Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the inherited unsafe speech evaluator with an offline-first, fail-closed Tamil word-assessment vertical slice and constrained adaptive policy while preserving the owned frontend design.

**Architecture:** A focused `app.vaakmitra_word` package owns typed evidence, audio checks, deterministic normalization, model adapters, embedding DTW, calibrated fusion, safe policy, and API mapping. Production readiness requires compatible real artifacts; core tests inject explicit fakes and cannot make production scoring ready.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, NumPy, SciPy, scikit-learn, pytest, React 18, Vite, Vitest, and optional NVIDIA NeMo in a separate model dependency manifest.

**Spec:** `VAAKMITRA_FINAL_SSOT.md` version 3.0.0. This plan is procedural; the SSOT remains the sole normative source.

## Global Constraints

- Work only in `D:\VaakMitra-Integrated-Backend`; both VaakMitra source roots are read-only.
- Decisions are exactly PASS, RETRY, or UNSCORABLE.
- Missing or incompatible artifacts, invalid capture, and insufficient evidence never produce PASS.
- Browser transcript, English Wav2Vec, fake MFCCs, face inference, voice conversion, and score floors cannot affect correctness.
- Audio and voice-derived representations are ephemeral and never persisted or synchronized.
- Bandit actions are therapist-filtered and cannot affect correctness thresholds.
- Core CI is synthetic engineering evidence; real model tests use a separate marker.
- Child-facing UI never displays “wrong,” “bad,” or numeric accuracy.

---

### Task 1: Canonical contracts

**Files:**
- Create: `backend/app/vaakmitra_word/__init__.py`
- Create: `backend/app/vaakmitra_word/contracts.py`
- Test: `backend/tests/vaakmitra_word/test_contracts.py`

**Interfaces:** Produces `Decision`, `ReasonCode`, `EvidenceItem`, `AssessmentEvidence`, `AudioQuality`, `WordCandidate`, `AssessmentResult`, `ModelEvidence`, and `ModelReadiness`. `AssessmentResult.to_legacy()` is the sole compatibility mapping.

- [x] **Step 1: Write failing validation tests.**

```python
def test_unscorable_legacy_mapping_has_no_score():
    result = AssessmentResult.unscorable(ReasonCode.MODEL_UNAVAILABLE)
    assert result.to_legacy()["matched"] is None
    assert result.to_legacy()["accuracy"] is None

def test_pass_requires_probability(base_fields):
    with pytest.raises(ValidationError):
        AssessmentResult(decision=Decision.PASS, word_match_probability=None, **base_fields)
```

- [x] **Step 2: Run `python -m pytest tests/vaakmitra_word/test_contracts.py -q` from `backend`; confirm missing imports fail.**
- [x] **Step 3: Implement frozen Pydantic contracts, range checks, and decision invariants.**
- [x] **Step 4: Re-run the test and require exit code 0.**
- [x] **Step 5: Commit as `feat: add canonical word assessment contracts`.**

### Task 2: Embedding DTW and reference bank

**Files:**
- Create: `backend/app/vaakmitra_word/dtw.py`
- Test: `backend/tests/vaakmitra_word/test_dtw.py`

**Interfaces:** `cosine_dtw_distance(query, reference, band_ratio=0.20) -> float`; `ReferenceBank.best_distance(word_id, embeddings, model_hash) -> float | None`.

- [x] **Step 1: Write failing numerical tests.**

```python
def test_identical_sequences_have_zero_distance():
    x = np.array([[1., 0.], [0., 1.]], dtype=np.float32)
    assert cosine_dtw_distance(x, x) == pytest.approx(0.0)

@pytest.mark.parametrize("bad", [np.empty((0, 2)), np.array([[np.nan, 0.]])])
def test_invalid_sequences_are_rejected(bad):
    with pytest.raises(InvalidEmbeddingSequence):
        cosine_dtw_distance(bad, np.ones((2, 2), dtype=np.float32))
```

- [x] **Step 2: Run the focused test and confirm failure.**
- [x] **Step 3: Implement cosine frame cost, a 20% Sakoe-Chiba band expanded by length difference, path-length normalization, and version/hash mismatch as unavailable.**
- [x] **Step 4: Re-run focused tests and require exit code 0.**
- [x] **Step 5: Commit as `feat: add representation-level DTW`.**

### Task 3: Calibrated fusion and abstention

**Files:**
- Create: `backend/app/vaakmitra_word/calibration.py`
- Create: `backend/model_artifacts/README.md`
- Test: `backend/tests/vaakmitra_word/test_calibration.py`

**Interfaces:** `EvidenceCalibrator.decide(evidence, quality) -> FusionDecision`; artifact fields are feature order, means, scales, coefficients, intercept, retry/pass thresholds, all cross-hashes, and approved flag.

- [x] **Step 1: Write failing hard-gate tests.**

```python
def test_dtw_alone_cannot_pass(calibrator, good_quality):
    assert calibrator.decide(dtw_only(0.99), good_quality).decision is Decision.UNSCORABLE

def test_invalid_audio_is_unscorable(calibrator, clipped_quality):
    assert calibrator.decide(full_evidence(), clipped_quality).reason_code is ReasonCode.INVALID_AUDIO

def test_unapproved_artifact_is_not_ready():
    assert EvidenceCalibrator(unapproved_artifact()).ready is False
```

- [x] **Step 2: Run the focused test and confirm failure.**
- [x] **Step 3: Implement deterministic logistic inference, explicit missing masks, multi-family PASS, disagreement gate, typed reasons, and approved/hash compatibility validation.**
- [x] **Step 4: Document that committed test artifacts are synthetic and real artifacts install outside Git.**
- [x] **Step 5: Re-run tests and commit as `feat: add fail-closed evidence calibration`.**

### Task 4: Safe policy and LinUCB

**Files:**
- Create: `backend/app/vaakmitra_word/policy.py`
- Create: `backend/app/vaakmitra_word/bandit.py`
- Test: `backend/tests/vaakmitra_word/test_policy.py`
- Test: `backend/tests/vaakmitra_word/test_bandit.py`

**Interfaces:** `SafeAdaptivePolicy.choose(result, state, therapist_constraints, bandit) -> PolicyDecision`; `LinUCBPolicy.choose(context, eligible_actions) -> BanditChoice`; `update(action, context, reward_components) -> None`.

- [x] **Step 1: Write failing safety tests.**

```python
def test_stop_overrides_pass_and_bandit(policy, pass_result, state):
    state.stop_requested = True
    choice = policy.choose(pass_result, state, constraints(), unsafe_bandit())
    assert choice.next_action == "safe_end"
    assert choice.selected_by == "safety_override"

def test_time_seated_is_not_reward():
    with pytest.raises(InvalidRewardComponent):
        reward_value({"time_seated": 3.0})
```

- [x] **Step 2: Run both focused tests and confirm failure.**
- [x] **Step 3: Implement deterministic priority, eligible-action filtering, deterministic/shadow/active modes, and LinUCB using `A=I`, `b=0`, `theta=A^-1 b`, and `theta·x + alpha*sqrt(x·A^-1·x)`.**
- [x] **Step 4: Re-run tests and require exit code 0.**
- [x] **Step 5: Commit as `feat: add constrained adaptive word policy`.**

### Task 5: Audio validation and auxiliary normalization

**Files:**
- Create: `backend/app/vaakmitra_word/audio.py`
- Create: `backend/app/vaakmitra_word/normalization.py`
- Test: `backend/tests/vaakmitra_word/test_audio.py`
- Test: `backend/tests/vaakmitra_word/test_normalization.py`

**Interfaces:** `decode_wav_bytes(data) -> DecodedAudio`; `validate_audio(samples, rate) -> AudioQuality`; `create_normalized_view(decoded, config) -> NormalizedView`.

- [x] **Step 1: Write failing decode/quality tests.**

```python
def test_wav_becomes_mono_float32_16khz():
    result = decode_wav_bytes(stereo_wav(sample_rate=8000))
    assert result.sample_rate == 16000
    assert result.samples.dtype == np.float32
    assert result.samples.ndim == 1

def test_clipping_is_invalid():
    q = validate_audio(np.ones(16000, dtype=np.float32), 16000)
    assert q.clipped and not q.valid
```

- [x] **Step 2: Write tests proving the original array is unchanged, transformed output is finite/non-clipping, and configured bounds are enforced.**
- [x] **Step 3: Implement PCM WAV decode/resample, duration/RMS/clipping checks, labelled degraded energy VAD, DC removal, and peak-safe loudness normalization. Formant/rate hooks remain explicitly disabled until approved artifacts exist.**
- [x] **Step 4: Re-run focused tests and require exit code 0.**
- [x] **Step 5: Commit as `feat: add word audio preprocessing`.**

### Task 6: Model/classifier protocols and readiness registry

**Files:**
- Create: `backend/app/vaakmitra_word/model.py`
- Create: `backend/app/vaakmitra_word/classifier.py`
- Create: `backend/app/vaakmitra_word/registry.py`
- Create: `backend/requirements-model.txt`
- Test: `backend/tests/vaakmitra_word/test_registry.py`
- Test: `backend/tests/vaakmitra_word/test_model_adapter.py`

**Interfaces:** `AcousticModel.infer(samples, sample_rate) -> ModelEvidence`; `WordClassifier.predict(embeddings, word_id) -> EvidenceItem`; `ServiceRegistry.scoring_readiness() -> ModelReadiness`.

- [x] **Step 1: Write failing missing-model, hash-mismatch, and fake-not-production-ready tests.**
- [x] **Step 2: Implement protocols, unavailable adapters, SHA-256 verification, lazy NeMo import/load, typed runtime errors, and registry cross-hash checks.**
- [x] **Step 3: Keep NeMo/PyTorch out of core requirements; pin the validated stack in `requirements-model.txt` only after environment compatibility is confirmed. An unavailable environment remains explicitly unready.**
- [x] **Step 4: Run focused tests and require exit code 0.**
- [x] **Step 5: Commit as `feat: add fail-closed IndicConformer registry`.**

### Task 7: Orchestration and privacy

**Files:**
- Create: `backend/app/vaakmitra_word/assessment.py`
- Create: `backend/app/vaakmitra_word/privacy.py`
- Test: `backend/tests/vaakmitra_word/test_assessment.py`
- Test: `backend/tests/vaakmitra_word/test_privacy.py`

**Interfaces:** `WordAssessmentService.assess(audio_bytes, context) -> AssessmentResult`; `validate_sync_payload(payload) -> None` recursively rejects forbidden or unknown fields.

- [x] **Step 1: Write fake-model integration tests for PASS, RETRY, model-failure UNSCORABLE, and cleanup after exception/cancellation.**
- [x] **Step 2: Write recursive privacy tests.**

```python
@pytest.mark.parametrize("payload", [
    {"metadata": {"audio": "x"}},
    {"items": [{"embedding_vector": [1, 2]}]},
    {"transcript": "அம்மா"},
])
def test_forbidden_data_is_rejected_at_any_depth(payload):
    with pytest.raises(SyncPolicyViolation):
        validate_sync_payload(payload)
```

- [x] **Step 3: Implement decode/quality, raw inference, optional normalized inference, classifier, DTW, fusion, and policy orchestration with guaranteed cleanup. Unavailable evidence remains explicit.**
- [x] **Step 4: Run focused tests and require exit code 0.**
- [x] **Step 5: Commit as `feat: orchestrate private word assessment`.**

### Task 8: FastAPI integration

**Files:**
- Create: `backend/app/vaakmitra_word/router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/routers/evaluation.py`
- Test: `backend/tests/vaakmitra_word/test_api.py`

**Interfaces:** Adds `POST /api/v1/word-assessments` and `GET /health/scoring`; delegates existing `POST /api/evaluate/speech`; disables the inherited face-analysis route.

- [x] **Step 1: Write failing TestClient tests for multipart fields, server-owned mapping, upload/MIME limits, 503 scoring health, legacy null score when unavailable, ignored browser transcript, and disabled face capability.**
- [x] **Step 2: Add a dependency-overridable canonical router, bounded upload read, safe reason mapping, and typed health.**
- [x] **Step 3: Remove English speech-evaluator warm-up/import and legacy scoring logic. Keep the request shape but delegate to the canonical service and `to_legacy()`.**
- [x] **Step 4: Run `python -m pytest tests/vaakmitra_word -q`, then `python -m pytest -q`; distinguish any proven pre-existing unrelated failures.**
- [x] **Step 5: Commit as `feat: expose safe Tamil word assessment API`.**

### Task 9: Frontend safety mapping

**Files:**
- Modify: exact evaluation caller/reducer/components found by `rg -n "evaluate/speech|accuracy|browser_transcript" frontend/src`.
- Test: corresponding colocated `*.test.js` and `*.test.jsx` files.

**Interfaces:** Consumes decision, nullable probability, reason code, response intent, and nullable legacy mapping; preserves routes/layout/styles/images/animations.

- [x] **Step 1: Write failing tests: PASS celebrates without percentage; RETRY is gentle; UNSCORABLE does not celebrate; null never renders `null%` or `0% accuracy`.**
- [x] **Step 2: Update only the API adapter and safety-critical copy. Remove browser transcript from the authoritative request.**
- [x] **Step 3: Run `npm test -- --run`, `npm run lint`, and `npm run build`.**
- [x] **Step 4: Commit as `fix: render safe word assessment outcomes`.**

### Task 10: Deployment and evidence

**Files:**
- Modify: `backend/.env.example`, `backend/Dockerfile`, `README.md`
- Create: `backend/scripts/verify_artifacts.py`
- Create: `backend/tests/vaakmitra_word/test_artifact_verifier.py`
- Create: `docs/WORD_MODEL_INSTALLATION.md`
- Create: `docs/VERIFICATION_STATUS.md`

**Interfaces:** `verify_artifacts.py --config PATH --json` exits nonzero on missing/hash/version/approval mismatch. Evidence status separates synthetic, real-model, device, privacy, and clinical proof.

- [x] **Step 1: Write failing verifier tests for missing file, wrong hash, cross-hash mismatch, unapproved calibration, and complete synthetic bundle.**
- [x] **Step 2: Implement verifier and fail-closed startup configuration. Production defaults never select fake artifacts.**
- [x] **Step 3: Document offline installation, hashes, private-LAN controls, start/health/canary/rollback commands, and technical-prototype disclaimer.**
- [x] **Step 4: Run backend tests, verifier, frontend tests/lint/build, `git diff --check`, and `git status --short`. A real-bundle verifier failure is recorded as a pending evidence gate, not hidden.**
- [x] **Step 5: Commit as `docs: add private edge deployment and evidence ledger`.**

## Self-review

- Spec coverage: contracts, DTW, calibration, adaptation, audio, model readiness, privacy, API, frontend, and deployment are mapped. Real child data, real-model canary, physical Unity/Android, packet capture, and clinical review remain evidence gates and cannot be fabricated by implementation.
- Type consistency: all shared contracts are created in Task 1 and consumed unchanged.
- Safety consistency: all unavailable/invalid paths end in UNSCORABLE; PASS requires calibrated multi-family evidence.
- Placeholder scan: no implementation placeholder is accepted as completion; deliberately unavailable production capabilities report typed readiness failures.
- Execution mode: inline execution is selected because the user already requested the build and did not request delegation.
