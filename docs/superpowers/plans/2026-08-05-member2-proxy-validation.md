# Member 2 Proxy Validation and Edge Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Member 2 technical-prototype path using licensed proxy data and development-hardware evidence while mechanically preventing unsupported clinical or tablet claims.

**Architecture:** Pure Python modeling modules validate immutable input manifests, compute CTC and proxy-calibration metrics, and assemble release evidence from hashed JSON artifacts. Existing ONNX runtime/export/quantization/benchmark modules remain the executable edge core; new tools add provenance and honest evidence gates without crossing Member 1 or Member 3 ownership.

**Tech Stack:** Python 3.11, NumPy, Pydantic 2, pytest, ONNX, ONNX Runtime, psutil, JSON/JSONL manifests.

## Global Constraints

- Implement only Member 2 scope; do not implement audio capture, VAD, Tamil G2P, forced alignment, persistence, synchronization, Unity, therapist APIs, or adaptive decisions.
- Run all audio/model processing locally; add no HTTP runtime dependency.
- Keep real audio, model weights, embeddings, probability matrices, and transcripts outside Git and logs.
- Treat adult, proxy, emulator, and laptop results as technical evidence only.
- Reject a validated-release claim unless therapist-labelled target-user and actual target-device evidence are present.
- Introduce every production behavior with a test that is observed failing for the intended reason.

---

### Task 1: Licensed Proxy Corpus Manifest

**Files:**
- Create: `modeling/data/__init__.py`
- Create: `modeling/data/corpus_manifest.py`
- Create: `modeling/manifests/tamil-proxy-corpus.example.json`
- Test: `backend/tests/unit/test_corpus_manifest.py`

**Interfaces:**
- Consumes: JSON with `schema_version`, dataset identity/revision/source/licence, population and label origin, local-only flag, and speaker-disjoint split records.
- Produces: `CorpusManifest.from_json(path)` and `CorpusManifest.digest()` for later evidence assembly.

```python
class CorpusSplit(BaseModel):
    name: Literal["train", "validation", "test"]
    speakers: tuple[str, ...]
    record_count: int = Field(gt=0)
    index_sha256: str

class CorpusManifest(BaseModel):
    schema_version: Literal["1.0"]
    dataset_id: str
    revision: str
    source_url: str
    license_spdx: str
    population: Literal["adult_tamil_proxy", "general_child_proxy", "target_user_child"]
    label_origin: Literal[
        "dataset_supplied_phonemes", "rule_based_proxy", "therapist_adjudicated"
    ]
    evidence_scope: Literal["engineering_proxy", "target_user_validation"]
    local_processing_only: bool
    splits: tuple[CorpusSplit, ...]

    @classmethod
    def from_json(cls, path: str | Path) -> "CorpusManifest": ...
    def digest(self) -> str: ...
```

- [ ] **Step 1: Write failing tests for missing licence, mutable revisions, unsafe evidence labels, duplicate speakers across splits, and a valid manifest.**

```python
def test_proxy_manifest_rejects_speaker_overlap() -> None:
    payload = valid_proxy_manifest()
    payload["splits"][1]["speakers"] = [payload["splits"][0]["speakers"][0]]
    with pytest.raises(ValueError, match="speaker-disjoint"):
        CorpusManifest.model_validate(payload)

def test_proxy_manifest_has_stable_canonical_digest() -> None:
    first = CorpusManifest.model_validate(valid_proxy_manifest())
    second = CorpusManifest.model_validate(dict(reversed(valid_proxy_manifest().items())))
    assert first.digest() == second.digest()
```
- [ ] **Step 2: Run `\.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_corpus_manifest.py -q` and verify failures are caused by the missing module.**
- [ ] **Step 3: Implement frozen Pydantic manifest types, validation, canonical JSON digesting, and the non-sensitive example manifest.**
- [ ] **Step 4: Re-run the focused tests and the complete backend suite.**
- [ ] **Step 5: Commit with `feat: validate proxy corpus provenance`.**

### Task 2: Frozen CTC Evaluation

**Files:**
- Create: `modeling/evaluation/__init__.py`
- Create: `modeling/evaluation/ctc_metrics.py`
- Create: `modeling/evaluation/evaluate_jsonl.py`
- Test: `backend/tests/unit/test_ctc_evaluation.py`

**Interfaces:**
- Consumes: reference phonemes, frame/token predictions, explicit blank token, population/evidence scope, and scorable state.
- Produces: `collapse_ctc_tokens`, `edit_distance`, `evaluate_records`, and a JSON CLI report with micro/macro PER, exact accuracy, error totals, count, and unscorable rate.

```python
@dataclass(frozen=True, slots=True)
class EvaluationRecord:
    utterance_id: str
    reference: tuple[str, ...]
    predicted_tokens: tuple[str, ...]
    blank_token: str
    population: str
    evidence_scope: str
    scorable: bool = True

def collapse_ctc_tokens(tokens: Sequence[str], blank_token: str) -> tuple[str, ...]: ...
def edit_distance(reference: Sequence[str], hypothesis: Sequence[str]) -> int: ...
def evaluate_records(records: Sequence[EvaluationRecord]) -> CtcEvaluationReport: ...
```

- [ ] **Step 1: Write failing literal tests for blank/repeat collapse, insertion/deletion/substitution distance, aggregation, and scope separation.**

```python
def test_ctc_collapse_removes_blank_and_collapses_only_adjacent_repeats() -> None:
    assert collapse_ctc_tokens(("<b>", "a", "a", "<b>", "a", "m"), "<b>") == (
        "a", "a", "m"
    )

def test_evaluation_reports_literal_micro_per() -> None:
    report = evaluate_records((record(("a", "m"), ("a", "n")),))
    assert report.total_errors == 1
    assert report.reference_tokens == 2
    assert report.micro_per == pytest.approx(0.5)
```
- [ ] **Step 2: Run the focused test and verify the missing evaluation module is the failure.**
- [ ] **Step 3: Implement deterministic metric dataclasses/functions and a JSONL CLI that rejects child/clinical scope for proxy records.**
- [ ] **Step 4: Run focused and full tests, then smoke-test `python -m modeling.evaluation.evaluate_jsonl --help`.**
- [ ] **Step 5: Commit with `feat: add frozen phoneme ctc evaluation`.**

### Task 3: Auditable Proxy Confidence Calibration

**Files:**
- Create: `modeling/calibration/__init__.py`
- Create: `modeling/calibration/proxy_calibration.py`
- Create: `modeling/calibration/calibrate_jsonl.py`
- Test: `backend/tests/unit/test_proxy_calibration.py`

**Interfaces:**
- Consumes: finite GOP/confidence values, binary proxy labels, fixed candidate thresholds, a false-accept ceiling, and unscorable examples.
- Produces: deterministic retry/coach/pass thresholds plus confusion counts, false-accept rate, expected calibration error, unscorable rate, and `proxy_not_therapist_calibrated` status.

```python
@dataclass(frozen=True, slots=True)
class ProxyCalibrationExample:
    example_id: str
    score: float | None
    acceptable: bool | None

def calibrate_proxy_thresholds(
    examples: Sequence[ProxyCalibrationExample],
    *,
    candidate_thresholds: Sequence[float],
    max_false_accept_rate: float,
) -> ProxyCalibrationReport: ...
```

- [ ] **Step 1: Write failing tests for threshold selection, false-accept enforcement, deterministic ties, invalid labels, and unscorable accounting.**

```python
def test_calibration_selects_lowest_threshold_within_false_accept_limit() -> None:
    report = calibrate_proxy_thresholds(
        examples((0.9, True), (0.8, True), (0.7, False), (0.1, False)),
        candidate_thresholds=(0.5, 0.75, 0.85),
        max_false_accept_rate=0.0,
    )
    assert report.pass_threshold == pytest.approx(0.75)
    assert report.false_accepts == 0
    assert report.calibration_status == "proxy_not_therapist_calibrated"
```
- [ ] **Step 2: Run the focused test and verify it fails because calibration behavior is absent.**
- [ ] **Step 3: Implement the pure calibration functions and JSONL CLI; reject any request to label the result therapist/clinical calibrated.**
- [ ] **Step 4: Run focused/full tests and CLI help.**
- [ ] **Step 5: Commit with `feat: add proxy confidence calibration`.**

### Task 4: Release Evidence and Android-Ready Gate

**Files:**
- Create: `modeling/release/__init__.py`
- Create: `modeling/release/evidence.py`
- Create: `modeling/release/assemble_evidence.py`
- Create: `modeling/manifests/android-package.example.json`
- Test: `backend/tests/unit/test_release_evidence.py`

**Interfaces:**
- Consumes: non-empty model/vocabulary/corpus/evaluation/calibration/comparison/benchmark files and their evidence scopes.
- Produces: hashed `technical_prototype` evidence JSON and a gate that permits `target_device_validated` only with therapist-target-user and actual-target-device reports.

```python
class EvidenceInput(BaseModel):
    kind: Literal[
        "model", "vocabulary", "corpus", "evaluation", "calibration", "comparison", "benchmark"
    ]
    path: Path
    evidence_scope: str

def assemble_release_evidence(
    inputs: Sequence[EvidenceInput], *, requested_status: str
) -> ReleaseEvidence: ...
```

- [ ] **Step 1: Write failing tests for artifact hashes, missing inputs, laptop-versus-target scope, unsupported clinical claims, and a valid prototype bundle.**

```python
def test_target_device_release_rejects_laptop_and_proxy_evidence(tmp_path: Path) -> None:
    inputs = complete_inputs(tmp_path, benchmark_scope="development_laptop")
    with pytest.raises(ValueError, match="actual target_device"):
        assemble_release_evidence(inputs, requested_status="target_device_validated")

def test_prototype_bundle_hashes_every_required_input(tmp_path: Path) -> None:
    report = assemble_release_evidence(
        complete_inputs(tmp_path), requested_status="technical_prototype"
    )
    assert {item.kind for item in report.artifacts} == {
        "model", "vocabulary", "corpus", "evaluation", "calibration", "comparison", "benchmark"
    }
```
- [ ] **Step 2: Run focused tests and verify failure due to missing release module.**
- [ ] **Step 3: Implement evidence records, canonical digesting, scope gates, CLI assembly, and Android package checklist schema.**
- [ ] **Step 4: Run focused/full tests and CLI help.**
- [ ] **Step 5: Commit with `feat: gate member 2 release evidence`.**

### Task 5: Reproducible End-to-End Technical-Prototype Evidence

**Files:**
- Create: `modeling/fixtures/create_synthetic_ctc_onnx.py`
- Create: `modeling/fixtures/__init__.py`
- Create: `benchmarks/manifests/synthetic-prototype.json`
- Modify: `README.md`
- Modify: `modeling/model_cards/ta-phoneme-ctc-baseline.md`
- Test: `backend/tests/integration/test_prototype_evidence_flow.py`

**Interfaces:**
- Consumes: deterministic synthetic audio and a tiny synthetic CTC ONNX graph generated locally.
- Produces: locally ignored FP32/INT8 artifacts plus aggregate comparison, development-laptop benchmark, and technical-prototype release reports.

```python
def create_synthetic_ctc_model(
    output_path: Path,
    *,
    vocabulary_size: int = 3,
    frame_shift_ms: float = 20.0,
) -> ArtifactRecord: ...
```

- [ ] **Step 1: Write a failing integration test for deterministic fixture creation and complete local evidence assembly.**

```python
def test_synthetic_model_is_nonempty_and_reproducible(tmp_path: Path) -> None:
    first = create_synthetic_ctc_model(tmp_path / "first.onnx")
    second = create_synthetic_ctc_model(tmp_path / "second.onnx")
    assert first.sha256 == second.sha256
    assert first.size_bytes > 0
```
- [ ] **Step 2: Run it and verify failure because the fixture generator is absent.**
- [ ] **Step 3: Implement the synthetic fixture generator and executable PowerShell command sequence; clearly mark every output synthetic/development-only.**
- [ ] **Step 4: Run FP32 inference, INT8 conversion, output comparison, benchmark, and evidence assembly locally; record only aggregate reports allowed by policy.**
- [ ] **Step 5: Update README/model card with proxy limitations, exact commands, and the external therapist/tablet validation gate.**
- [ ] **Step 6: Run the integration test and full quality gates.**
- [ ] **Step 7: Commit with `test: prove member 2 prototype evidence flow`.**

### Task 6: Final Requirement and Quality Audit

**Files:**
- Create: `docs/verification/member2-completion-report.md`
- Modify: `docs/architecture/member2-speech-intelligence.md`

**Interfaces:**
- Consumes: PRD Member 2 work packages M2.1-M2.5, their Definitions of Done, and fresh command output.
- Produces: a line-by-line status report separating verified engineering evidence from unavailable external validation.

- [ ] **Step 1: Run full pytest, Ruff, strict mypy, package build, all CLI help commands, `git diff --check`, and a repository secret/large-file scan.**
- [ ] **Step 2: Audit M2.1-M2.5 and record command evidence, artifact hashes, limitations, and exact follow-up commands for therapist/tablet evidence.**
- [ ] **Step 3: Re-run affected documentation and full quality checks after the audit.**
- [ ] **Step 4: Commit with `docs: record member 2 completion evidence`.**

Required verification commands:

```powershell
& .\.venv\Scripts\python.exe -m pytest backend\tests -q
& .\.venv\Scripts\python.exe -m ruff check backend\src backend\tests modeling benchmarks
& .\.venv\Scripts\python.exe -m mypy backend\src modeling benchmarks
& .\.venv\Scripts\python.exe -m build backend
& .\.venv\Scripts\python.exe -m modeling.evaluation.evaluate_jsonl --help
& .\.venv\Scripts\python.exe -m modeling.calibration.calibrate_jsonl --help
& .\.venv\Scripts\python.exe -m modeling.release.assemble_evidence --help
git diff --check
```
