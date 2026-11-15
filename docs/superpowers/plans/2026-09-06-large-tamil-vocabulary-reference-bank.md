# Large Tamil Vocabulary and Adult Reference Bank Implementation Plan

> **Execution:** Follow `superpowers:test-driven-development` task by task. The normative source is `VAAKMITRA_FINAL_SSOT.md` v3.1.0; the companion design is `docs/superpowers/specs/2026-09-06-large-tamil-vocabulary-reference-bank-design.md`.

**Goal:** Build a reproducible adult-data engineering pipeline for a dynamic 100-word Tamil vocabulary, a balanced 32–64-reference-per-word embedding bank, a closed-vocabulary classifier with at least 10,000 `OTHER` examples, adult-only engineering calibration, canaries, and an immutable fail-closed bundle.

**Architecture:** Versioned JSON manifests are the boundary between acquisition, preprocessing, embedding extraction, training, evaluation, and packaging. Every stage is deterministic, preserves provenance, emits hashes/reports, and rejects leakage or unknown licence status. Runtime continues to require an approved child-separated calibrator for `scoring_ready=true`.

**Stack:** Python 3.10/3.11, Pydantic 2, NumPy, SciPy, scikit-learn, soundfile, librosa where already compatible, AI4Bharat NeMo in the pinned WSL GPU runtime, FastAPI, React/Vite.

## Task 1: Versioned vocabulary registry

**Requirements:** DEC-003, DEC-016, CLS-001, CLS-004, DATA-012
**Files:**

- Create `backend/app/vaakmitra_word/vocabulary.py`
- Create `backend/data/vocabulary/ta-v1-intended.json`
- Create `backend/tests/vaakmitra_word/test_vocabulary.py`

1. Write failing tests that load the registry, require exactly 100 unique stable IDs and NFC Tamil canonical forms, distinguish scoreable words from teaching-only letters, reject duplicate IDs/text, and fail closed for inactive words.
2. Run `python -m pytest tests/vaakmitra_word/test_vocabulary.py -q` from `backend`; record the expected missing-module failure.
3. Implement immutable models and registry lookup without importing frontend constants.
4. Re-run the focused test, then `python -m pytest tests/vaakmitra_word -q`.
5. Commit: `feat: add versioned Tamil word registry`.

## Task 2: Dynamic curriculum/API integration

**Requirements:** DEC-002, DEC-003, DEC-016, MOD-008
**Files:**

- Modify `backend/app/vaakmitra_word/router.py`
- Modify `backend/app/routers/therapy.py`
- Modify `frontend/src/services/api.js`
- Modify the exact lesson/catalog components found by `rg -n "LESSONS|therapy/lessons|target_word" frontend/src backend/app`
- Add focused backend and frontend tests beside existing route/component tests

1. Write failing contract tests proving active vocabulary comes from the registry, legacy letter lessons are `scoreable=false`, inactive targets are unscorable, and UI handles more than six records without static fallbacks.
2. Run the focused backend/frontend tests and confirm failures describe the hardcoded ceiling.
3. Implement the authenticated vocabulary endpoint and registry-backed mappings while preserving existing layout and navigation.
4. Re-run focused tests plus frontend lint/build.
5. Commit: `feat: serve dynamic Tamil curriculum`.

## Task 3: Corpus/provenance schemas and licence gate

**Requirements:** DTW-001, DTW-002, DTW-007, DATA-001, DATA-007, DATA-008, DATA-010, DATA-011
**Files:**

- Create `backend/app/vaakmitra_word/corpus.py`
- Create `backend/scripts/corpus/validate_manifest.py`
- Create `backend/tests/vaakmitra_word/test_corpus.py`
- Create `backend/data/corpus/source_registry.json`

1. Write failing tests for required source revision, original ID, speaker pseudonym, canonical word ID, checksum, duration, split, licence/provenance status, parent/augmentation provenance, and rejection of unknown/incompatible licences.
2. Confirm focused RED.
3. Implement frozen manifest models, JSONL streaming validation, deterministic IDs, checksum verification, and leakage checks.
4. Verify GREEN and add CLI integration tests against temporary fixtures.
5. Commit: `feat: add governed Tamil corpus manifests`.

## Task 4: Resumable adult corpus acquisition

**Requirements:** DATA-001, DATA-007, DATA-010, DATA-011
**Files:**

- Create `backend/scripts/corpus/acquire.py`
- Create `backend/app/vaakmitra_word/acquisition.py`
- Create `backend/tests/vaakmitra_word/test_acquisition.py`
- Update `backend/data/corpus/source_registry.json`

1. Write failing tests against a local HTTP fixture for resumable range downloads, checksum mismatch, interrupted archives, source revision pinning, and no silent overwrite.
2. Confirm RED.
3. Implement adapters for approved source types (Hugging Face snapshot/file, indexed HTTP archive, and owned local recordings) using a configurable cache outside Git.
4. Verify GREEN, then inventory available disk before real downloads.
5. Acquire only sources whose live terms and revision are recorded; emit an acquisition report with accepted/rejected sources and exact hashes.
6. Commit: `feat: add resumable adult corpus acquisition`.

## Task 5: Deterministic preprocessing and deduplication

**Requirements:** AUD-001..012, DTW-007, DATA-003, DATA-007, DATA-011
**Files:**

- Create `backend/app/vaakmitra_word/corpus_preprocessing.py`
- Create `backend/scripts/corpus/preprocess.py`
- Create `backend/tests/vaakmitra_word/test_corpus_preprocessing.py`

1. Write failing tests for 16 kHz mono conversion, invalid/no-speech/clipped rejection, transcript-to-canonical mapping, exact hash duplicates, acoustic near-duplicates, speaker-disjoint split assignment, deterministic seed, and preserved parent provenance.
2. Confirm RED.
3. Implement streaming preprocessing that writes derived build assets outside Git and an append-only manifest/report inside the configured output root.
4. Verify GREEN on controlled audio fixtures and run a small real-data smoke batch.
5. Commit: `feat: preprocess and deduplicate Tamil corpus`.

## Task 6: GPU embedding extraction

**Requirements:** DEC-004, MOD-001..008, DTW-001, DATA-008
**Files:**

- Create `backend/scripts/model/extract_embeddings.py`
- Create `backend/app/vaakmitra_word/embedding_store.py`
- Create `backend/tests/vaakmitra_word/test_embedding_store.py`
- Update `docs/GPU_INFERENCE_EVIDENCE.md`

1. Write failing CPU-side tests for shard schema, model/vocabulary/source hashes, finite `[frames, dimensions]` arrays, resumability, and corrupt-shard rejection.
2. Confirm RED and implement the store/export boundary.
3. Run a real RTX 4060 WSL canary using the pinned model/runtime, then extract accepted adult corpus embeddings in resumable shards.
4. Record command, model hash, code commit, GPU/runtime, counts, failures, throughput, and peak memory.
5. Commit: `feat: extract governed Tamil embeddings`.

## Task 7: Balanced reference-bank selection and safe DTW aggregation

**Requirements:** DEC-006, DEC-017, DTW-001..007, DATA-010..012
**Files:**

- Modify `backend/app/vaakmitra_word/dtw.py`
- Modify `backend/app/vaakmitra_word/artifacts.py`
- Create `backend/scripts/model/build_reference_bank.py`
- Modify/add `backend/tests/vaakmitra_word/test_dtw.py`
- Add `backend/tests/vaakmitra_word/test_reference_builder.py`

1. Write failing tests proving one prolific speaker cannot dominate, aggregation uses the best three distinct speakers, under-eight-speaker words remain inactive, each speaker contributes at most four references, 32–64 bounds hold, and hash/version mismatch is unavailable.
2. Confirm RED.
3. Implement metadata-rich references and deterministic diversity selection; return aggregate distance plus coverage rather than a naked minimum.
4. Verify GREEN and build the real adult bank from extracted embeddings.
5. Emit per-word counts/speaker/source diversity and rejection reasons; no unsupported word may be silently activated.
6. Commit: `feat: build balanced Tamil reference bank`.

## Task 8: Closed-vocabulary classifier training/export

**Requirements:** DEC-007, CLS-001..005, DATA-003, DATA-004, DATA-010..012
**Files:**

- Modify `backend/app/vaakmitra_word/classifier.py`
- Modify `backend/app/vaakmitra_word/artifacts.py`
- Create `backend/scripts/model/train_classifier.py`
- Create `backend/tests/vaakmitra_word/test_classifier_training.py`
- Modify `backend/tests/vaakmitra_word/test_classifier.py`

1. Write failing tests for the versioned pooling schema, stable label order, mandatory `OTHER`, class balancing, speaker-disjoint splits, deterministic fit, artifact hash fields, and absent-class unscorable behavior.
2. Confirm RED.
3. Implement masked mean/std pooling plus a lightweight deterministic linear model and held-out probability calibration.
4. Verify GREEN and train on active adult targets plus at least 10,000 accepted `OTHER`/confusable examples.
5. Export metrics/confusion/report and immutable classifier artifact.
6. Commit: `feat: train Tamil closed-word classifier`.

## Task 9: Adult-only engineering calibration

**Requirements:** DEC-008, DEC-015, FUS-001..007, DATA-001, DATA-008
**Files:**

- Extend `backend/app/vaakmitra_word/calibration.py`
- Create `backend/scripts/model/calibrate_engineering.py`
- Create `backend/tests/vaakmitra_word/test_calibration_training.py`
- Create `backend/model_artifacts/ENGINEERING_CALIBRATION.md`

1. Write failing tests for speaker-disjoint fitting, missing masks, deterministic model selection, threshold ordering, metric computation, bootstrap intervals, and forced `approved=false` for adult-only datasets.
2. Confirm RED.
3. Implement logistic/isotonic comparison and select by predeclared held-out adult safety objective; never reuse the final evaluation split.
4. Verify GREEN and fit the real adult engineering calibrator.
5. Export false-PASS/false-RETRY, abstention, ECE, Brier, AUROC/AUPRC, word confusion, and confidence intervals with the explicit non-clinical label.
6. Commit: `feat: calibrate adult engineering evidence`.

## Task 10: Adult/therapist canary suite

**Requirements:** MOD-008, DATA-008, GATE-02, OPS readiness canary
**Files:**

- Extend bundle canary schema in `backend/app/vaakmitra_word/artifacts.py`
- Create `backend/app/vaakmitra_word/canary.py`
- Create `backend/scripts/model/build_canaries.py`
- Create `backend/scripts/model/run_canaries.py`
- Add `backend/tests/vaakmitra_word/test_canary.py`

1. Write failing tests for per-active-word positive coverage, category-level confusables, audio-quality negatives, training/reference leakage rejection, exact expected constraints, consent/reviewer metadata, and immutable hashes.
2. Confirm RED.
3. Implement canary build/run reports. Automated technical acceptance is separate from human/clinical approval.
4. Map owned therapist recordings only when their exact target/segment and permitted use are explicit; otherwise report them as pending candidates.
5. Run real-model canaries and record latency distribution and failures.
6. Commit: `feat: add Tamil release canary suite`.

## Task 11: Immutable engineering bundle

**Requirements:** DATA-008, FUS-007, OPS-003, GATE-02, GATE-03
**Files:**

- Modify `backend/app/vaakmitra_word/artifacts.py`
- Modify `backend/scripts/verify_artifacts.py`
- Add/modify `backend/tests/vaakmitra_word/test_artifact_verifier.py`
- Create `backend/scripts/model/build_bundle.py`
- Update `docs/WORD_MODEL_INSTALLATION.md`
- Update `docs/VERIFICATION_STATUS.md`

1. Write failing tests for cross-hashes of model, vocabulary, classifier, reference bank, adult calibrator, dataset manifest, canary manifest, and code commit; test that adult-only calibration can be engineering-complete but never scoring-ready.
2. Confirm RED.
3. Implement deterministic packaging, signing input manifest, rollback metadata, and verifier output.
4. Build and verify the real engineering bundle.
5. Commit: `build: package Tamil engineering bundle`.

## Task 12: Full verification and evidence reconciliation

**Requirements:** GATE-01..06, EV-UNIT, EV-MODEL, EV-CAL, EV-PRIV, EV-DEVICE, EV-CLIN

1. Run from `backend`: `python -m pytest -q`.
2. Run from `frontend`: `npm test -- --run`, `npm run lint`, `npm run build`.
3. Run artifact verification and real canary commands in the pinned WSL GPU runtime.
4. Run `git diff --check` and `git status --short`.
5. Reconcile `docs/VERIFICATION_STATUS.md` line by line. Mark adult corpus/classifier/reference/calibration/canary evidence complete only where logs and hashes prove it.
6. Keep child-separated calibration, child validation, clinical approval, privacy packet capture, and physical-device evidence pending unless independently supplied and verified.
7. Commit: `docs: reconcile Tamil corpus evidence`.

## Expected final boundary

Completing this plan can produce a reproducible, large, adult-data engineering bundle and fully implemented application plumbing. It cannot legitimately set clinical calibration `approved=true`, report target-child accuracy, or make production scoring ready without the explicitly excluded child-validation and clinician-approval evidence.
