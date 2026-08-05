# Dual-Track Tamil Model Strengthening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement every CPU-verifiable component of the full IndicConformer phoneme-reference track and the teacher-distilled Android edge track, leaving only real CUDA training jobs and their generated checkpoints/metrics outstanding.

**Architecture:** A shared, immutable Tamil phoneme/data/evidence contract feeds two PyTorch model paths. Track A wraps a pinned IndicConformer-compatible encoder with a phoneme CTC head and staged freeze schedule; Track B trains compact Conformer and Conv-BiGRU students with supervised CTC and hidden-representation distillation. Pure modules implement controlled-confusion calibration, robustness stress tests, promotion gates, ONNX parity, and physical-device report validation without crossing Member 1 alignment or Member 3 decision ownership.

**Tech Stack:** Python 3.11, Pydantic 2, NumPy, PyTorch 2.11 CPU, torchaudio 2.11 CPU, ONNX, ONNX Runtime, pytest, Ruff, strict mypy, JSON/JSONL manifests.

## Global Constraints

- Implement only Member 2 scope; Member 1 retains production G2P, pronunciation variants, syllabification, forced alignment, and audio validation.
- Strategy 1 is the compact teacher-distilled edge path; Strategy 2 is full IndicConformer phoneme fine-tuning.
- Never reinterpret IndicConformer text-token posteriors as phoneme posteriors.
- Keep audio, transcripts, hidden features, probability matrices, checkpoints, and model weights local and ignored by Git.
- Default to no child audio; transformed adult speech is robustness evidence, not child-domain validation.
- Every external source requires immutable provenance and dataset-specific license/access approval before materialization.
- `expert_approved=false`, `production_ready=false`, and proxy-only outcome labels remain mandatory without external Tamil/therapist evidence.
- The adult-Tamil test split is speaker-, utterance-, and audio-digest-disjoint and frozen before model selection.
- Strong adult proxy targets are PER `<=0.20`, controlled-confusion AUROC `>=0.90`, proxy false-accept rate `<=0.05`, and ECE `<=0.05`; failed gates remain explicit failures.
- The edge target is compressed size `<=50 MB`, INT8 PER delta `<=0.01`, median absolute GOP delta `<=0.03`, and physical-Android model-only P95 `<=500 ms`.
- The current machine is CPU-only. CUDA-required training commands must fail with `gpu_required_for_full_training`; CPU smoke paths must remain executable.
- Introduce every production behavior with a focused test, observe the intended failure, then add the minimal implementation.

---

### Task 1: Shared Tamil Inventory Consensus Contract

**Files:**
- Create: `modeling/inventory/consensus.py`
- Create: `modeling/configs/tamil_phoneme_sources.json`
- Create: `modeling/manifests/tamil-phoneme-contract.example.json`
- Modify: `modeling/inventory/generate_inventory.py`
- Test: `backend/tests/unit/test_inventory_consensus.py`

**Interfaces:**
- Consumes: `InventorySource(source_id, revision, segments, source_scope)` records, Epitran lexicon units, and normalized exercise/corpus units.
- Produces: `build_candidate_inventory(...) -> CandidateInventory`, `CandidateInventory.digest()`, per-token provenance, core/extended classification, allophone mappings, unknown-token coverage, and a conflict ledger.

- [ ] **Step 1: Write failing literal tests for consensus, provenance, unresolved conflicts, stable blank index, and unknown-token rejection.**

```python
def test_consensus_keeps_blank_first_and_reports_source_disagreement() -> None:
    result = build_candidate_inventory(
        sources=(source("phoible-a", ("a", "m")), source("phoible-b", ("a", "n"))),
        observed_units=("a", "m", "n", "x"),
        allophones=(AllophoneRule(source="ŋ", canonical="n", provenance="fixture"),),
        version="ta-candidate-1",
    )
    assert result.tokens[0] == "<blank>"
    assert result.core_tokens == ("a",)
    assert result.extended_tokens == ("m", "n", "x")
    assert result.conflicts[0].token == "m"
    assert result.expert_approved is False
    assert result.production_ready is False
```

- [ ] **Step 2: Run `python -m pytest backend/tests/unit/test_inventory_consensus.py -q`; confirm the missing module is the failure.**
- [ ] **Step 3: Implement frozen Pydantic models, NFC normalization, deterministic ordering/digesting, source-count classification, conflict generation, allophone validation, and coverage reporting.**
- [ ] **Step 4: Add pinned PHOIBLE/Epitran source metadata and a non-production example contract; extend the CLI to merge the generated Epitran lexicon into consensus inputs.**
- [ ] **Step 5: Run focused tests, the existing inventory tests, Ruff, and strict mypy.**
- [ ] **Step 6: Commit with `feat: build Tamil inventory consensus contract`.**

### Task 2: Licensed Corpus Index and Leakage-Proof Splits

**Files:**
- Create: `modeling/data/corpus_index.py`
- Create: `modeling/data/build_corpus_index.py`
- Modify: `modeling/data/corpus_manifest.py`
- Modify: `modeling/data/source_preflight.py`
- Modify: `modeling/configs/tamil_research_sources.json`
- Create: `modeling/manifests/iisc-mile-tamil.example.json`
- Test: `backend/tests/unit/test_corpus_index.py`
- Test: `backend/tests/unit/test_source_preflight.py`

**Interfaces:**
- Consumes: local JSONL `CorpusRecord(utterance_id, speaker_id, audio_sha256, transcript_sha256, sample_rate_hz, duration_ms)` without paths or transcript text.
- Produces: `freeze_corpus_index(records, assignments, source) -> FrozenCorpusIndex` and aggregate split manifests whose digests bind every record while omitting sensitive fields.

- [ ] **Step 1: Write failing tests proving that speaker, utterance, and audio-digest overlap are rejected and that 16 kHz finite-duration records produce stable split digests.**

```python
def test_freeze_rejects_same_audio_digest_across_speakers() -> None:
    records = (record("u1", "s1", "a" * 64), record("u2", "s2", "a" * 64))
    with pytest.raises(ValueError, match="audio digest"):
        freeze_corpus_index(records, {"s1": "train", "s2": "test"}, source())
```

- [ ] **Step 2: Run focused tests and confirm they fail because the index contract is absent.**
- [ ] **Step 3: Implement immutable record/source/index models, split assignment validation, canonical digests, and privacy-safe JSON output.**
- [ ] **Step 4: Add IISc-MILE/OpenSLR-127 metadata with `CC-BY-2.0`, adult-proxy scope, 16 kHz mono constraints, immutable audit revision, and no automatic bulk download.**
- [ ] **Step 5: Implement the JSONL CLI, refusing overwrite, transcript content, file paths, unreviewed licenses, or unfrozen source revisions.**
- [ ] **Step 6: Run focused/full data tests, CLI help, Ruff, and mypy.**
- [ ] **Step 7: Commit with `feat: freeze leakage-safe Tamil corpus indexes`.**

### Task 3: IndicConformer Access, Runtime, and Freeze-Schedule Preflight

**Files:**
- Create: `modeling/teacher/__init__.py`
- Create: `modeling/teacher/preflight.py`
- Create: `modeling/teacher/run_preflight.py`
- Create: `modeling/training/stages.py`
- Create: `modeling/configs/full_indicconformer_phoneme.example.json`
- Test: `backend/tests/unit/test_teacher_preflight.py`
- Test: `backend/tests/unit/test_training_stages.py`

**Interfaces:**
- Consumes: pinned teacher configuration, token/access probe state, installed dependency versions, CUDA state, and validation PER history.
- Produces: `evaluate_teacher_preflight(...) -> TeacherPreflightReport`, stable codes `model_access_not_authorized` and `gpu_required_for_full_training`, plus `select_trainable_parameters(model, stage) -> FreezeReport`.

- [ ] **Step 1: Write failing tests for absent authorization, wrong revision, CPU smoke permission, full-run CUDA refusal, and exact head/top-block/full-encoder parameter selection.**

```python
def test_full_training_preflight_refuses_cpu_only_host() -> None:
    report = evaluate_teacher_preflight(valid_probe(cuda_available=False), mode="full_train")
    assert report.ready is False
    assert report.code == "gpu_required_for_full_training"

def test_head_stage_freezes_everything_except_phoneme_head() -> None:
    report = select_trainable_parameters(fixture_model(), TrainingStage.HEAD_ONLY)
    assert report.trainable_groups == ("phoneme_head",)
```

- [ ] **Step 2: Run the focused tests and observe missing-symbol failures.**
- [ ] **Step 3: Implement pure preflight models and stage selection without printing tokens, paths, or credentials.**
- [ ] **Step 4: Implement a CLI that inspects local dependency/token/CUDA state and emits JSON; network authorization remains an explicit injected probe rather than an access-control bypass.**
- [ ] **Step 5: Add staged optimizer configuration: head only, top encoder blocks, optional full encoder only after validation improvement.**
- [ ] **Step 6: Run focused tests, CLI CPU-smoke/full-train cases, Ruff, and mypy.**
- [ ] **Step 7: Commit with `feat: gate IndicConformer phoneme training`.**

### Task 4: Full Reference Phoneme Head and CPU Smoke Training

**Files:**
- Create: `modeling/training/phoneme_head.py`
- Create: `modeling/training/ctc_batch.py`
- Create: `modeling/training/smoke_full_track.py`
- Test: `backend/tests/unit/test_phoneme_head.py`
- Test: `backend/tests/integration/test_full_track_cpu_smoke.py`

**Interfaces:**
- Consumes: encoder outputs shaped `[batch, frames, hidden]`, frame lengths, padded phoneme targets, and a vocabulary with blank index zero.
- Produces: `PhonemeCtcModel`, finite `ctc_loss(...)`, validated `PhonemeBatch`, and a deterministic CPU-smoke report/checkpoint manifest generated from a tiny fixture encoder.

- [ ] **Step 1: Write failing tests for output dimensions, blank index, length propagation, invalid/non-finite tensors, CTC loss, and the head-only gradient boundary.**

```python
def test_phoneme_head_outputs_vocab_logits_and_head_only_gradients() -> None:
    model = PhonemeCtcModel(FixtureEncoder(8), hidden_size=8, vocabulary_size=5)
    select_trainable_parameters(model, TrainingStage.HEAD_ONLY)
    logits, lengths = model(torch.zeros(2, 800), torch.tensor([800, 640]))
    assert logits.shape[:2] == (2, lengths.max().item())
    assert logits.shape[-1] == 5
```

- [ ] **Step 2: Run tests and confirm missing implementation failures.**
- [ ] **Step 3: Implement the encoder protocol, phoneme CTC wrapper, batch validation, finite-loss guard, gradient clipping, and resume-safe hash-linked checkpoint metadata.**
- [ ] **Step 4: Implement deterministic CPU smoke training with fixture data; ensure the report says `cpu_smoke_only`, never trained IndicConformer.**
- [ ] **Step 5: Run focused/integration tests twice to verify deterministic metrics and checkpoint metadata.**
- [ ] **Step 6: Commit with `feat: add full-track phoneme ctc training core`.**

### Task 5: Compact Student Architectures

**Files:**
- Create: `modeling/distillation/students.py`
- Create: `modeling/configs/student_conformer.example.json`
- Create: `modeling/configs/student_conv_bigru.example.json`
- Test: `backend/tests/unit/test_student_models.py`

**Interfaces:**
- Consumes: mono `[batch, samples]` audio and sample lengths.
- Produces: `CompactConformerCtc`, `CompactConvBiGruCtc`, `StudentOutput(logits, hidden, frame_lengths)`, parameter/serialized-size estimates, and configuration validation.

- [ ] **Step 1: Write failing tests for dynamic batch/sample lengths, strictly positive frame lengths, stable parameter counts, vocabulary logits, and rejection of oversized/invalid configurations.**
- [ ] **Step 2: Run focused tests and observe the missing models.**
- [ ] **Step 3: Implement one shared convolutional frontend, a batch-first compact Transformer/Conformer-style encoder, and an improved two-layer bidirectional GRU baseline.**
- [ ] **Step 4: Return hidden representations before the CTC head and expose deterministic `parameter_report()` values used by release comparison.**
- [ ] **Step 5: Run focused tests, TorchScript/forward smoke, Ruff, and mypy.**
- [ ] **Step 6: Commit with `feat: add compact Tamil phoneme students`.**

### Task 6: Distillation Objectives and CPU Training Step

**Files:**
- Create: `modeling/distillation/losses.py`
- Create: `modeling/distillation/training.py`
- Create: `modeling/training/smoke_student_track.py`
- Test: `backend/tests/unit/test_distillation_losses.py`
- Test: `backend/tests/integration/test_student_track_cpu_smoke.py`

**Interfaces:**
- Consumes: student hidden/logits, cached teacher hidden features, masks, phoneme targets, and configured non-negative loss weights.
- Produces: masked projected representation loss, relational frame-similarity loss, optional collapsed-sequence consistency, weighted finite total loss, and deterministic one-epoch CPU smoke reports for both students.

- [ ] **Step 1: Write failing hand-derived loss tests, including padding invariance, projection shape validation, all-masked rejection, non-finite rejection, and proof that text-posterior KL is not accepted.**

```python
def test_masked_representation_loss_ignores_padded_frames() -> None:
    student = torch.tensor([[[1.0], [9.0]]])
    teacher = torch.tensor([[[0.0], [100.0]]])
    assert masked_representation_loss(student, teacher, torch.tensor([[True, False]])) == 1.0
```

- [ ] **Step 2: Run focused tests and verify intended missing-function failures.**
- [ ] **Step 3: Implement projection, masked smooth-L1 representation loss, normalized Gram-matrix relational loss, supervised CTC composition, and finite-gradient checks.**
- [ ] **Step 4: Integrate validated teacher-feature caches by digest and reject model-revision/audio-digest mismatches.**
- [ ] **Step 5: Implement CPU smoke loops for both students and emit hash-linked reports with `distillation_smoke_only`.**
- [ ] **Step 6: Run focused/integration tests, Ruff, and mypy.**
- [ ] **Step 7: Commit with `feat: add phoneme student distillation core`.**

### Task 7: Controlled Confusions and Confidence Ensemble

**Files:**
- Create: `modeling/calibration/controlled_confusions.py`
- Create: `modeling/calibration/confidence_ensemble.py`
- Modify: `modeling/calibration/proxy_calibration.py`
- Test: `backend/tests/unit/test_controlled_confusions.py`
- Test: `backend/tests/unit/test_confidence_ensemble.py`
- Modify: `backend/tests/unit/test_proxy_calibration.py`

**Interfaces:**
- Consumes: expected phones, phonological feature map, GOP margin, alignment confidence, normalized entropy, posterior margin, blank dominance, duration validity, scorer agreement, and model disagreement.
- Produces: deterministic substitution/length/gemination/sequence corruptions, `ProxyConfidenceFeatures`, conservative scalar confidence or unscorable reason, AUROC/Brier/ECE/FAR/FRR/bootstrap metrics, and phone/class-pooled thresholds.

- [ ] **Step 1: Write failing tests for each corruption type and ensure originals are immutable and every negative has a machine-readable reason.**
- [ ] **Step 2: Write failing confidence tests using literal feature vectors, including weak-evidence `unscorable`, normalized entropy bounds, and conservative model disagreement.**
- [ ] **Step 3: Extend calibration tests for hand-derived AUROC, Brier score, false-reject rate, deterministic bootstrap intervals, and phone-to-class threshold fallback.**
- [ ] **Step 4: Run focused tests and confirm all new behaviors fail before implementation.**
- [ ] **Step 5: Implement pure corruption, ensemble, metric, and threshold functions; retain `proxy_pass`, `proxy_coach`, `retry`, and `unscorable` labels only.**
- [ ] **Step 6: Run focused/full calibration tests, Ruff, and mypy.**
- [ ] **Step 7: Commit with `feat: strengthen proxy pronunciation calibration`.**

### Task 8: Child-Like Robustness Stress Matrix

**Files:**
- Create: `modeling/robustness/__init__.py`
- Create: `modeling/robustness/transforms.py`
- Create: `modeling/robustness/report.py`
- Create: `modeling/configs/robustness_matrix.json`
- Test: `backend/tests/unit/test_robustness_transforms.py`
- Test: `backend/tests/unit/test_robustness_report.py`

**Interfaces:**
- Consumes: finite mono 16 kHz float waveform, seeded transform specifications, baseline/stressed PER and confidence/outcome values.
- Produces: deterministic rate, pitch/formant proxy, VTLN, pause, repetition, noise, gain, clipping, bandwidth, and resampling stresses plus aggregate degradation/order-inversion/unscorable-preference reports.

- [ ] **Step 1: Write failing tests for shape/range/finiteness, seed determinism, moderate label preservation metadata, and severe-corruption unscorable expectations.**
- [ ] **Step 2: Write failing report tests for absolute/relative PER degradation, confidence delta, ordering inversions, and severe confident-decision violations.**
- [ ] **Step 3: Run focused tests and verify missing modules.**
- [ ] **Step 4: Implement dependency-light Torch/NumPy transforms with explicit parameters and no claim that transformed audio is child speech.**
- [ ] **Step 5: Implement the frozen matrix loader and aggregate report with `transformation_robustness_only` evidence scope.**
- [ ] **Step 6: Run focused tests, deterministic smoke application, Ruff, and mypy.**
- [ ] **Step 7: Commit with `feat: add child-like acoustic stress testing`.**

### Task 9: Promotion Gates, ONNX Parity, and Quantization Evidence

**Files:**
- Create: `modeling/evaluation/promotion.py`
- Create: `modeling/validation/model_parity.py`
- Modify: `modeling/export/export_onnx.py`
- Modify: `modeling/quantization/quantize_onnx.py`
- Test: `backend/tests/unit/test_promotion_gates.py`
- Test: `backend/tests/unit/test_model_parity.py`
- Test: `backend/tests/integration/test_dual_track_onnx.py`

**Interfaces:**
- Consumes: full/student evaluation, calibration, robustness, artifact-size, GOP-parity, and latency reports.
- Produces: pass/fail/not-measured results for every fixed threshold, PyTorch/ONNX/INT8 parity summaries, dynamic-sample export metadata, and integrity-bound Android package manifests.

- [ ] **Step 1: Write failing tests for every numeric gate, including exact boundary behavior and explicit `not_measured` rather than implicit pass.**
- [ ] **Step 2: Write failing parity tests for logit shape, max/mean absolute error, greedy sequence agreement, PER delta, and median absolute GOP delta.**
- [ ] **Step 3: Run focused tests and observe missing implementations.**
- [ ] **Step 4: Implement pure promotion and parity reports with conservative aggregation.**
- [ ] **Step 5: Extend export metadata to bind model/config/vocabulary hashes and dynamic sample axes; keep text-posterior exports invalid.**
- [ ] **Step 6: Export and dynamically quantize both tiny student fixtures on CPU; expose a calibration-data adapter for static INT8 where operators support it, then run ONNX Runtime comparison and static mobile operator audit.**
- [ ] **Step 7: Run focused/integration tests, Ruff, mypy, and CLI help.**
- [ ] **Step 8: Commit with `feat: gate dual-track edge model promotion`.**

### Task 10: Physical Android Benchmark Evidence Contract

**Files:**
- Create: `modeling/mobile/device_benchmark.py`
- Create: `modeling/mobile/parse_device_report.py`
- Create: `modeling/manifests/device-benchmark.example.json`
- Test: `backend/tests/unit/test_device_benchmark.py`

**Interfaces:**
- Consumes: JSON exported by an AndroidX benchmark harness or physical-device service with device fingerprint, physical/emulator classification, provider, repetitions, cold load, latency samples, peak memory, thermal state, model digest, and offline assertion.
- Produces: validated median/P95 metrics and an edge-gate result; emulator or missing-network-denial evidence cannot satisfy physical-device promotion.

- [ ] **Step 1: Write failing tests for percentile calculation, physical-device requirements, provider validation, digest mismatch, insufficient repetitions, missing offline assertion, and emulator rejection.**
- [ ] **Step 2: Run focused tests and observe missing module failure.**
- [ ] **Step 3: Implement frozen input/report models, deterministic percentile interpolation, privacy-field rejection, and service-neutral Firebase/AWS provenance fields.**
- [ ] **Step 4: Implement CLI parsing and a synthetic example report that is explicitly non-promotable.**
- [ ] **Step 5: Run focused tests and CLI help, Ruff, and mypy.**
- [ ] **Step 6: Commit with `feat: validate physical Android benchmark evidence`.**

### Task 11: Dual-Track Comparison, Evidence Assembly, and Operator Documentation

**Files:**
- Create: `modeling/release/dual_track_comparison.py`
- Create: `modeling/release/compare_dual_tracks.py`
- Modify: `modeling/release/evidence.py`
- Modify: `README.md`
- Modify: `modeling/training/README.md`
- Modify: `modeling/model_cards/ta-phoneme-ctc-baseline.md`
- Modify: `docs/architecture/member2-speech-intelligence.md`
- Modify: `docs/verification/member2-completion-report.md`
- Test: `backend/tests/unit/test_dual_track_comparison.py`
- Test: `backend/tests/integration/test_dual_track_cpu_evidence.py`

**Interfaces:**
- Consumes: Track A, Conformer-student, Conv-BiGRU-student, and historical-proxy reports plus promotion results.
- Produces: deterministic ranking with no promotion when mandatory evidence is absent, hash-linked technical-prototype evidence, exact CPU and future CUDA commands, and an outstanding-work ledger limited to GPU-generated runs and external clinical/device evidence.

- [ ] **Step 1: Write failing tests proving that quality, exportability, size, calibration, and physical-device gates all affect selection and that missing mandatory evidence cannot win.**
- [ ] **Step 2: Write a failing CPU integration test that runs both smoke tracks, exports student fixtures, evaluates parity, assembles comparison evidence, and reports GPU work as blocked rather than passed.**
- [ ] **Step 3: Run focused/integration tests and observe the missing comparison behavior.**
- [ ] **Step 4: Implement comparison records, stable tie-breaking, hash linkage, and evidence-scope enforcement.**
- [ ] **Step 5: Update operator documentation with exact inventory, corpus-index, preflight, CPU-smoke, future CUDA, export, calibration, robustness, device-ingestion, and comparison commands.**
- [ ] **Step 6: Update completion evidence line-by-line: code-complete CPU scope, missing real IndicConformer checkpoint/metrics, missing therapist/child evidence, and missing physical-device execution.**
- [ ] **Step 7: Run focused integration and full quality gates.**
- [ ] **Step 8: Commit with `docs: complete CPU dual-track implementation evidence`.**

### Task 12: Final Repository Verification

**Files:**
- Modify only if verification exposes a tested defect.

**Interfaces:**
- Consumes: all implementation and generated aggregate reports.
- Produces: a clean feature branch with reproducible verification output and no tracked private/model artifacts.

- [ ] **Step 1: Run the complete backend test suite.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend\tests -q
```

- [ ] **Step 2: Run Ruff, strict mypy, package build, and all new CLI help/smoke commands.**

```powershell
& .\.venv\Scripts\python.exe -m ruff check backend\src backend\tests modeling benchmarks
& .\.venv\Scripts\python.exe -m mypy backend\src modeling benchmarks
& .\.venv\Scripts\python.exe -m build backend
& .\.venv\Scripts\python.exe -m modeling.teacher.run_preflight --help
& .\.venv\Scripts\python.exe -m modeling.training.smoke_full_track --help
& .\.venv\Scripts\python.exe -m modeling.training.smoke_student_track --help
& .\.venv\Scripts\python.exe -m modeling.mobile.parse_device_report --help
& .\.venv\Scripts\python.exe -m modeling.release.compare_dual_tracks --help
```

- [ ] **Step 3: Run `git diff --check`, inspect tracked file sizes, scan tracked paths for secrets/private audio/model artifacts, and verify `git status --short`.**
- [ ] **Step 4: If all gates pass, invoke the finishing-a-development-branch workflow and report the exact GPU-only and external-evidence remainder without claiming clinical completion.**
