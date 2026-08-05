# Corpus, Inventory Review, and GPU Runbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Materialize and verify OpenSLR-127 locally, freeze privacy-safe speaker-disjoint evidence, generate a corpus-backed Tamil phoneme candidate and clinician review packet, and deliver an executable staged IndicConformer/distillation GPU runbook.

**Architecture:** Private recordings, transcripts, identifiers, and generated features remain under ignored `modeling/artifacts/`. Pure Python modules validate archive members, WAV/transcript pairs, deterministic speaker assignments, clinician-review state, and aggregate evidence. Committed JSON/CSV/Markdown contains only provenance, hashes, aggregate metrics, candidate acoustic units, bounded review examples, and commands for a separate CUDA host.

**Tech Stack:** Python 3.11, stdlib `tarfile`, `wave`, `hashlib`, `csv`, Pydantic 2, Epitran, PyTorch/NeMo GPU runbook, pytest, Ruff, strict mypy, PowerShell/curl for resumable download.

## Global Constraints

- Use only OpenSLR-127's official CC BY 2.0 archive URL and record the exact retrieval URL.
- Store the 13 GB archive, extracted audio/transcripts, private JSONL, assignments, and feature caches only under `modeling/artifacts/corpora/openslr-127/`.
- Never commit audio, full transcripts, paths, speaker IDs, utterance IDs, checkpoints, `.nemo`, `.onnx`, or feature tensors.
- A locally computed archive SHA-256 is `archive_sha256`; do not claim it is publisher-supplied.
- Preserve `expert_approved=false` and `production_ready=false` until a separately hash-bound clinician approval manifest is imported.
- Split by speaker before phoneme generation, augmentation, feature extraction, pseudo-labelling, or batching.
- Unknown phones are excluded or unscorable; they never map silently.
- Full IndicConformer and real student training remain CUDA jobs; local execution produces the corpus/inventory artifacts and exact GPU commands only.

---

### Task 1: Archive Integrity and Safe-Member Contract

**Files:**
- Create: `modeling/data/archive_safety.py`
- Test: `backend/tests/unit/test_archive_safety.py`

**Interfaces:**
- Consumes: `Path` to a tar.gz archive and a resolved extraction root.
- Produces: `sha256_file(path) -> str`, `inspect_tar_archive(path, extraction_root) -> ArchiveInspection`, and a validated tuple of regular-file/directory member names.

- [ ] **Step 1: Write failing tests for SHA-256, valid nested members, absolute paths, `..` traversal, Windows drive paths, symlinks/hardlinks, device nodes, and duplicate normalized destinations.**

```python
def test_inspection_rejects_parent_traversal_before_extraction(tmp_path: Path) -> None:
    archive = write_tar(tmp_path / "bad.tar.gz", {"../escape.txt": b"x"})
    with pytest.raises(ValueError, match="unsafe archive member"):
        inspect_tar_archive(archive, tmp_path / "extract")
    assert not (tmp_path / "escape.txt").exists()
```

- [ ] **Step 2: Run `python -m pytest backend/tests/unit/test_archive_safety.py -q` and verify missing-module failure.**
- [ ] **Step 3: Implement streaming SHA-256 and fail-closed tar metadata inspection without extracting any member.**
- [ ] **Step 4: Add `extract_validated_archive(...)` that extracts only the previously validated regular files/directories under the resolved root and refuses a non-empty destination.**
- [ ] **Step 5: Run focused tests, Ruff, and strict mypy.**
- [ ] **Step 6: Commit with `feat: validate OpenSLR archive extraction`.**

### Task 2: OpenSLR-127 Pairing, WAV Validation, and Speaker Splits

**Files:**
- Create: `modeling/data/openslr127.py`
- Test: `backend/tests/unit/test_openslr127.py`

**Interfaces:**
- Consumes: extracted `train/test` trees containing `audio_files` and `trans_files` plus an archive SHA-256.
- Produces: private `MaterializedRecord`, aggregate `CorpusMaterializationReport`, deterministic `assign_speakers(...)`, and inputs compatible with existing `CorpusRecord`/`freeze_corpus_index`.

- [ ] **Step 1: Write failing fixture tests for WAV/text pairing, NFC transcript hashing, 16 kHz mono PCM enforcement, non-empty Tamil transcript enforcement, official-split speaker overlap detection, deterministic validation selection, and privacy-safe aggregate serialization.**

```python
def test_materializer_rejects_stereo_audio_without_committing_path(tmp_path: Path) -> None:
    make_pair(tmp_path, split="train", stem="ISTL_0000202_0000009", channels=2)
    report = inspect_extracted_corpus(tmp_path, archive_sha256="a" * 64)
    assert report.accepted_count == 0
    assert report.rejections["invalid_wav_channels"] == 1
    assert str(tmp_path) not in report.model_dump_json()
```

- [ ] **Step 2: Run `python -m pytest backend/tests/unit/test_openslr127.py -q` and verify missing-module failure.**
- [ ] **Step 3: Implement corpus-root discovery, stem pairing, strict UTF-8/NFC transcript handling, WAV header validation, byte/text digests, duration calculation, and stable rejection codes.**
- [ ] **Step 4: Derive the speaker from the stable utterance identifier prefix, reject identifiers that do not expose a validated speaker component, and report identifier-pattern counts before freezing.**
- [ ] **Step 5: Retain the official test set only when speaker-disjoint; otherwise deterministically reassign speakers using SHA-256 with split-policy version `speaker-sha256-80-10-10-v1`. Select validation speakers only from official train when official test is retained.**
- [ ] **Step 6: Implement private JSONL/assignment writers under ignored storage and aggregate report/frozen-index writers that contain no identifiers, paths, or transcript text. Refuse overwrite.**
- [ ] **Step 7: Run focused tests, existing corpus-index tests, Ruff, and strict mypy.**
- [ ] **Step 8: Commit with `feat: materialize OpenSLR Tamil corpus`.**

### Task 3: Materialization CLI and Provenance Evidence

**Files:**
- Create: `modeling/data/materialize_openslr127.py`
- Create: `modeling/manifests/iisc-mile-tamil.snapshot.example.json`
- Modify: `README.md`
- Modify: `modeling/training/README.md`
- Test: `backend/tests/integration/test_openslr127_materialization.py`

**Interfaces:**
- Consumes: `--archive`, `--extract-root`, `--private-output-dir`, `--aggregate-report`, and `--frozen-index`.
- Produces: archive inspection, optional safe extraction, validated private records/assignments, aggregate evidence, and frozen `CorpusSource(revision_basis="archive_sha256")` index.

- [ ] **Step 1: Write a failing end-to-end integration test using a real tiny tar.gz with three speakers and literal expected aggregate counts/digests; assert that rerunning refuses overwrite.**
- [ ] **Step 2: Run the integration test and verify the CLI module is missing.**
- [ ] **Step 3: Implement explicit `inspect`, `extract`, and `index` phases so interrupted work can resume without repeating completed verified phases. Bind every phase to the archive digest.**
- [ ] **Step 4: Emit source URL, retrieval timestamp supplied by the caller, local archive digest/size, tar-integrity status, split policy, aggregate durations/counts, frozen index digest, and rejection counts.**
- [ ] **Step 5: Document the official resumable download command:**

```powershell
curl.exe -L --fail --retry 8 --retry-all-errors --continue-at - `
  --output modeling/artifacts/corpora/openslr-127/mile_tamil_asr_corpus.tar.gz.part `
  https://openslr.trmal.net/resources/127/mile_tamil_asr_corpus.tar.gz
```

- [ ] **Step 6: Run focused tests, CLI help, Ruff, and strict mypy.**
- [ ] **Step 7: Commit with `feat: add resumable Tamil corpus workflow`.**

### Task 4: Clinician Review Contract and Approval Import

**Files:**
- Create: `modeling/inventory/clinician_review.py`
- Create: `modeling/inventory/build_review_packet.py`
- Create: `modeling/manifests/tamil-phoneme-approval.example.json`
- Test: `backend/tests/unit/test_clinician_review.py`

**Interfaces:**
- Consumes: `CandidateInventory`, corpus token frequencies, bounded word/pronunciation examples, review CSV decisions, and a hash-bound approval JSON.
- Produces: deterministic token/pronunciation review rows, conflict/coverage JSON, `validate_approval(...) -> ApprovedInventoryContract`, and immutable provisional/reviewed artifacts.

- [ ] **Step 1: Write failing tests proving provisional output cannot self-approve, incomplete review rows fail, unknown decision values fail, replacement phones must exist, approval hashes must match, and approved import never mutates the provisional contract.**

```python
def test_approval_rejects_reviewed_inventory_digest_mismatch() -> None:
    manifest = approval(inventory_sha256="0" * 64)
    with pytest.raises(ValueError, match="inventory digest mismatch"):
        validate_approval(manifest, candidate_inventory())
```

- [ ] **Step 2: Run focused tests and verify missing-module failure.**
- [ ] **Step 3: Implement strict models for `approve`, `reject`, `replace`, and `needs_discussion`; require a decision for every token/conflict and every sampled pronunciation row.**
- [ ] **Step 4: Implement separate approved-contract creation with reviewer role, review date, organization reference, reviewed artifact digests, and no reviewer name/contact requirement.**
- [ ] **Step 5: Run focused tests, Ruff, and strict mypy.**
- [ ] **Step 6: Commit with `feat: add clinician phoneme review contract`.**

### Task 5: Corpus-Backed Candidate and Review Packet

**Files:**
- Modify: `modeling/inventory/generate_inventory.py`
- Create: `modeling/inventory/corpus_lexicon.py`
- Create: `docs/review/tamil-phoneme-inventory/README.md`
- Test: `backend/tests/unit/test_corpus_lexicon.py`
- Test: `backend/tests/integration/test_clinician_review_packet.py`

**Interfaces:**
- Consumes: private normalized transcript stream, pinned PHOIBLE/Epitran catalog, explicit allophone rules, sample seed, and maximum example count.
- Produces: candidate JSON, lexicon digest, token-frequency CSV, bounded pronunciation-review CSV, conflicts/unknown JSON, and approval template with `review_pending` status.

- [ ] **Step 1: Write failing tests for Unicode tokenization, deterministic unique-word extraction, long-vowel preservation, repeated-consonant gemination targets, unknown exclusion, stratified bounded examples, and absence of full transcripts/private IDs in committed outputs.**
- [ ] **Step 2: Run focused/integration tests and verify missing behavior.**
- [ ] **Step 3: Implement streaming corpus-word extraction and Epitran transliteration without loading audio. Keep the full lexicon private; expose only digests, frequencies, and bounded review examples.**
- [ ] **Step 4: Extend inventory generation to bind corpus/archive/lexicon hashes and emit review inputs without changing the candidate's approval flags.**
- [ ] **Step 5: Implement packet generation with stable CSV headers and machine-readable conflict/coverage evidence.**
- [ ] **Step 6: Run focused tests, inventory regressions, CLI help, Ruff, and strict mypy.**
- [ ] **Step 7: Commit with `feat: generate clinician Tamil phoneme packet`.**

### Task 6: IndicConformer and Student GPU Runbook

**Files:**
- Create: `modeling/training/gpu/README.md`
- Create: `modeling/training/gpu/environment.yaml`
- Create: `modeling/training/gpu/full-reference.yaml`
- Create: `modeling/training/gpu/student-conformer.yaml`
- Create: `modeling/training/gpu/student-conv-bigru.yaml`
- Create: `modeling/training/gpu/run_stages.ps1`
- Create: `modeling/training/gpu/run_distillation.ps1`
- Test: `backend/tests/unit/test_gpu_runbook_configs.py`

**Interfaces:**
- Consumes: reviewed inventory path/digest, frozen private train/validation/test manifests, pinned IndicConformer revision, CUDA device, and output artifact root.
- Produces: validated environment/training configurations and exact preflight, head-only, top-block, optional-full, feature extraction, two-student training, evaluation, export, and comparison commands.

- [ ] **Step 1: Write failing configuration tests for pinned model/revision, blank index zero, exact staged learning rates, top-block count four, conditional full unfreeze, BF16/FP16 fallback, gradient clipping, seeds, resume checkpoints, required input digests, distillation objectives, and promotion thresholds.**
- [ ] **Step 2: Run focused tests and verify files are missing.**
- [ ] **Step 3: Add pinned configuration files and scripts that fail before GPU work unless access, AI4Bharat NeMo, CUDA, reviewed inventory, archive digest, and frozen manifests match.**
- [ ] **Step 4: Document cloud-GPU sizing, checkpoint cadence, resume procedure, metrics, failure triage, artifact upload/download hashes, and commands that never print tokens.**
- [ ] **Step 5: Run config tests, PowerShell parser checks, Ruff, and strict mypy.**
- [ ] **Step 6: Commit with `docs: add Tamil model GPU execution runbook`.**

### Task 7: Execute the Real OpenSLR-127 Materialization

**Files:**
- Local ignored: `modeling/artifacts/corpora/openslr-127/**`
- Create: `benchmarks/reports/openslr127-corpus-evidence.json`
- Create: `modeling/manifests/iisc-mile-tamil.snapshot.json`
- Create: `docs/review/tamil-phoneme-inventory/tamil-phoneme-candidate.json`
- Create: `docs/review/tamil-phoneme-inventory/token-review.csv`
- Create: `docs/review/tamil-phoneme-inventory/pronunciation-review.csv`
- Create: `docs/review/tamil-phoneme-inventory/conflicts-and-coverage.json`
- Create: `docs/review/tamil-phoneme-inventory/approval-manifest.json`

**Interfaces:**
- Consumes: official downloaded archive and completed Tasks 1-6.
- Produces: verified local corpus, private manifests, aggregate frozen evidence, candidate inventory, and clinician packet.

- [ ] **Step 1: Start/resume the official mirror download and record URL plus UTC retrieval start.**
- [ ] **Step 2: Verify final byte count, rename `.part` to the immutable archive name, compute SHA-256, run tar integrity/safety inspection, and record UTC completion.**
- [ ] **Step 3: Safely extract, pair and validate all records; inspect actual identifier patterns before accepting speaker derivation. Stop if the corpus cannot prove speaker identity.**
- [ ] **Step 4: Freeze speaker-disjoint private assignments and committed aggregate corpus evidence.**
- [ ] **Step 5: Generate the complete private lexicon, provisional candidate, bounded clinician review packet, and approval template.**
- [ ] **Step 6: Verify every committed artifact contains no audio path, full transcript, speaker/utterance ID, child identity, credential, or unapproved claim.**
- [ ] **Step 7: Commit aggregate evidence and the clinician packet with `data: freeze OpenSLR Tamil review evidence`.**

### Task 8: Final Verification and Handoff

**Files:**
- Modify only if verification exposes a tested defect.

**Interfaces:**
- Consumes: all code, configs, aggregate evidence, and clinician packet.
- Produces: clean branch and exact clinician/GPU next actions.

- [ ] **Step 1: Run `python -m pytest backend/tests -q`.**
- [ ] **Step 2: Run Ruff, strict mypy, package build, materializer/inventory/GPU CLI help and config validation.**
- [ ] **Step 3: Run `git diff --check`, secret scans, tracked-size scans, and model/audio/private-identifier artifact scans.**
- [ ] **Step 4: Confirm the working tree contains no tracked corpus/model/private artifacts and that every review artifact remains explicitly pending.**
- [ ] **Step 5: Invoke `superpowers:finishing-a-development-branch`, report exact corpus/inventory outputs, and provide the clinician and CUDA-host handoff commands.**

