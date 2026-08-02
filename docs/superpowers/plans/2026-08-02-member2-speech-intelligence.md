# Member 2 Speech Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Backend Member 2's offline Tamil acoustic-runtime contracts, phoneme CTC probability validation, GOP/confidence scoring, syllable aggregation, ONNX integrity/runtime support, and reproducible edge benchmark tooling.

**Architecture:** A Python 3.11 package separates public contracts from acoustic runtimes and pure scoring functions. Member 1 supplies validated in-memory audio and forced alignment; Member 2 supplies time-indexed phoneme log probabilities and evidence-based scoring; Member 3 consumes only the resulting structured score contract. Model weights remain external, locally packaged, and hash-verified.

**Tech Stack:** Python 3.11, NumPy, Pydantic 2, pytest, optional ONNX/ONNX Runtime and psutil tooling.

## Global Constraints

- Implement only Member 2 scope; do not implement audio capture, VAD, G2P, forced alignment, persistence, sync, Unity, therapist APIs, or adaptive decisions.
- All inference and scoring operate locally without cloud APIs or HTTP dependencies.
- Accept only validated mono 16 kHz audio for acoustic inference.
- Never log or serialize audio, embeddings, full phoneme-probability arrays, free-speech transcripts, direct child identity, or diagnostic output.
- Every result carries model, vocabulary, and scoring versions.
- Invalid or low-confidence evidence returns `unscorable` or `retry` without a negative pronunciation judgement.
- Model artifacts and real speech data are ignored by Git; only synthetic fixtures, schemas, manifests, and aggregate reports are committed.
- Tests must precede production behavior and be observed failing for the expected missing behavior.

---

## File Map

- `backend/pyproject.toml`: package metadata, dependencies, pytest configuration, and optional model-tool extras.
- `backend/src/vaakmitra/contracts/*.py`: typed inputs and outputs shared with Members 1 and 3.
- `backend/src/vaakmitra/ctc/*.py`: vocabulary and log-probability contract validation.
- `backend/src/vaakmitra/scoring/*.py`: GOP, confidence, categories, and syllable aggregation.
- `backend/src/vaakmitra/pipeline/assessment.py`: orchestration limited to Member 2 runtime and scoring stages.
- `backend/src/vaakmitra/acoustic/*.py`: runtime protocol, model metadata/integrity, and ONNX adapter.
- `backend/src/vaakmitra/privacy/safe_logging.py`: allow-listed non-sensitive log records.
- `modeling/export/export_onnx.py`: source-model export entry point and manifest generation.
- `modeling/quantization/quantize_onnx.py`: explicit FP32-to-INT8 conversion.
- `benchmarks/run_benchmark.py`: warmup, cold load, latency percentile, size, and memory reporting.
- `backend/tests/`: unit, contract, integration, privacy, and synthetic fixture coverage.
- `docs/contracts/`: Member 1/2 and Member 2/3 integration documentation.
- `modeling/model_cards/`: honest baseline model card with evidence limitations.

---

### Task 1: Repository Skeleton, Contracts, and Privacy Defaults

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `backend/pyproject.toml`
- Create: `backend/src/vaakmitra/__init__.py`
- Create: `backend/src/vaakmitra/contracts/acoustic.py`
- Create: `backend/src/vaakmitra/contracts/alignment.py`
- Create: `backend/src/vaakmitra/contracts/scoring.py`
- Create: `backend/src/vaakmitra/privacy/safe_logging.py`
- Test: `backend/tests/contracts/test_contracts.py`
- Test: `backend/tests/unit/test_safe_logging.py`

**Interfaces:**
- Consumes: validated waveform metadata from Member 1 and alignment records from Member 1.
- Produces: `AcousticOutput`, `AlignedPhoneme`, `AlignmentResult`, `PhonemeScore`, `SyllableScore`, and `AssessmentResult` Pydantic models.

- [ ] **Step 1: Create package metadata, the empty package root, and failing contract/privacy tests**

```python
def test_acoustic_output_rejects_probability_width_mismatch() -> None:
    with pytest.raises(ValueError, match="vocabulary_size"):
        AcousticOutput(
            log_probabilities=np.zeros((2, 3), dtype=np.float32),
            frame_shift_ms=20.0,
            model_version="ta-ctc-1.0.0",
            vocabulary_version="ta-phones-1.0.0",
            blank_index=0,
            vocabulary_size=4,
        )


def test_safe_log_event_rejects_voice_derived_fields() -> None:
    with pytest.raises(ValueError, match="forbidden"):
        safe_log_event("inference", {"audio": [0.1], "model_version": "v1"})
```

- [ ] **Step 2: Create the isolated environment, install the editable development package, and verify missing-module failures**

Run: `py -3.11 -m venv .venv`

Run: `.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"`

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/contracts/test_contracts.py backend/tests/unit/test_safe_logging.py -q`

Expected: collection fails because `vaakmitra.contracts` and `vaakmitra.privacy` do not exist.

- [ ] **Step 3: Add packaging and minimal typed contracts**

```python
class AcousticOutput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    log_probabilities: np.ndarray
    frame_shift_ms: float = Field(gt=0)
    model_version: str = Field(min_length=1)
    vocabulary_version: str = Field(min_length=1)
    blank_index: int = Field(ge=0)
    vocabulary_size: int = Field(gt=1)

    @model_validator(mode="after")
    def validate_shape(self) -> "AcousticOutput":
        if self.log_probabilities.ndim != 2:
            raise ValueError("log_probabilities must have shape [frames, vocabulary_size]")
        if self.log_probabilities.shape[1] != self.vocabulary_size:
            raise ValueError("probability width must equal vocabulary_size")
        return self
```

`safe_log_event` accepts only `attempt_id`, versions, status/reason codes, tensor shapes, provider name, and aggregate timing fields.

- [ ] **Step 4: Run focused tests and then the package test suite**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/contracts/test_contracts.py backend/tests/unit/test_safe_logging.py -q`

Expected: all focused tests pass with no warnings.

- [ ] **Step 5: Commit the independently testable skeleton**

```powershell
git add .gitignore README.md backend
git commit -m "feat: scaffold member 2 speech contracts"
```

---

### Task 2: CTC Vocabulary and Log-Probability Validation

**Files:**
- Create: `backend/src/vaakmitra/ctc/__init__.py`
- Create: `backend/src/vaakmitra/ctc/vocabulary.py`
- Create: `backend/src/vaakmitra/ctc/probabilities.py`
- Create: `backend/configs/phoneme_vocabulary.example.json`
- Test: `backend/tests/unit/test_ctc_vocabulary.py`
- Test: `backend/tests/unit/test_ctc_probabilities.py`

**Interfaces:**
- Consumes: ordered phoneme tokens, blank token, version, and frame-level log probabilities.
- Produces: `PhonemeVocabulary`, `validate_log_probabilities(array, vocabulary) -> None`, and `frame_times_ms(frame_count, frame_shift_ms) -> np.ndarray`.

- [ ] **Step 1: Write failing behavior tests**

```python
def test_vocabulary_requires_exactly_one_blank() -> None:
    with pytest.raises(ValueError, match="blank"):
        PhonemeVocabulary(version="v1", tokens=("a", "m"), blank_token="<blank>")


def test_log_probabilities_must_normalize_per_frame() -> None:
    vocab = PhonemeVocabulary(version="v1", tokens=("<blank>", "a"), blank_token="<blank>")
    invalid = np.log(np.array([[0.8, 0.8]], dtype=np.float32))
    with pytest.raises(ValueError, match="normalize"):
        validate_log_probabilities(invalid, vocab)
```

- [ ] **Step 2: Run tests and confirm both fail because symbols are missing**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_ctc_vocabulary.py backend/tests/unit/test_ctc_probabilities.py -q`

Expected: collection fails for missing `PhonemeVocabulary` and validation functions.

- [ ] **Step 3: Implement immutable vocabulary and numerical validation**

```python
@dataclass(frozen=True, slots=True)
class PhonemeVocabulary:
    version: str
    tokens: tuple[str, ...]
    blank_token: str = "<blank>"

    def __post_init__(self) -> None:
        if not self.version.strip() or not self.tokens:
            raise ValueError("vocabulary version and tokens are required")
        if len(set(self.tokens)) != len(self.tokens):
            raise ValueError("vocabulary tokens must be unique")
        if self.tokens.count(self.blank_token) != 1:
            raise ValueError("vocabulary must contain exactly one blank token")
```

Validation uses a stable log-sum-exp calculation and a fixed tolerance of `1e-4` without modifying the input array.

- [ ] **Step 4: Run CTC tests and full suite**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_ctc_vocabulary.py backend/tests/unit/test_ctc_probabilities.py -q`

Expected: all CTC tests pass.

- [ ] **Step 5: Commit CTC contracts**

```powershell
git add backend/src/vaakmitra/ctc backend/configs backend/tests/unit/test_ctc_*.py
git commit -m "feat: validate phoneme CTC probability contract"
```

---

### Task 3: GOP, Confidence Gating, and Syllable Aggregation

**Files:**
- Create: `backend/src/vaakmitra/scoring/__init__.py`
- Create: `backend/src/vaakmitra/scoring/gop.py`
- Create: `backend/src/vaakmitra/scoring/confidence.py`
- Create: `backend/src/vaakmitra/scoring/syllables.py`
- Create: `backend/configs/scoring.default.json`
- Test: `backend/tests/unit/test_gop.py`
- Test: `backend/tests/unit/test_confidence.py`
- Test: `backend/tests/unit/test_syllables.py`

**Interfaces:**
- Consumes: `AcousticOutput`, `AlignmentResult`, `PhonemeVocabulary`, and versioned `ScoringConfig`.
- Produces: `score_aligned_phonemes(...) -> tuple[PhonemeScore, ...]` and `aggregate_syllables(...) -> tuple[SyllableScore, ...]`.

- [ ] **Step 1: Write failing hand-derived GOP and gating tests**

```python
def test_gop_uses_strongest_non_blank_competitor() -> None:
    segment = np.log(np.array([[0.05, 0.70, 0.25], [0.05, 0.60, 0.35]]))
    score = phoneme_gop(segment, expected_index=1, blank_index=0)
    expected_margin = np.mean(np.log([0.70, 0.60])) - np.mean(np.log([0.25, 0.35]))
    assert score == pytest.approx(1.0 / (1.0 + np.exp(-expected_margin)))


def test_low_alignment_confidence_is_unscorable() -> None:
    result = score_alignment(fixture_output(), fixture_alignment(confidence=0.2), fixture_config())
    assert result.status == "unscorable"
    assert result.reason == "alignment_low_confidence"
    assert result.phoneme_scores == ()
```

- [ ] **Step 2: Run scoring tests and confirm missing-function failures**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_gop.py backend/tests/unit/test_confidence.py backend/tests/unit/test_syllables.py -q`

Expected: collection fails for missing scoring functions.

- [ ] **Step 3: Implement the documented baseline formula and aggregation**

```python
def phoneme_gop(segment: np.ndarray, expected_index: int, blank_index: int) -> float:
    expected = segment[:, expected_index].mean()
    competitors = np.delete(segment, (blank_index, expected_index), axis=1)
    strongest = competitors.mean(axis=0).max()
    margin = float(expected - strongest)
    return 1.0 / (1.0 + math.exp(-margin))
```

Confidence is `acoustic_weight * acoustic_separation + alignment_weight * segment_confidence`. Configuration validation requires both weights in `[0, 1]`, a sum of one, monotonic score thresholds, and monotonic confidence thresholds. Syllable aggregation weights each phoneme by aligned frame duration.

- [ ] **Step 4: Run scoring tests and full suite**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_gop.py backend/tests/unit/test_confidence.py backend/tests/unit/test_syllables.py -q`

Expected: all scoring tests pass, including invalid bounds, unknown phoneme, empty segment, and unscorable propagation.

- [ ] **Step 5: Commit scoring behavior**

```powershell
git add backend/src/vaakmitra/scoring backend/configs/scoring.default.json backend/tests/unit/test_gop.py backend/tests/unit/test_confidence.py backend/tests/unit/test_syllables.py
git commit -m "feat: add GOP and confidence scoring"
```

---

### Task 4: Member 2 Assessment Pipeline

**Files:**
- Create: `backend/src/vaakmitra/acoustic/__init__.py`
- Create: `backend/src/vaakmitra/acoustic/base.py`
- Create: `backend/src/vaakmitra/pipeline/__init__.py`
- Create: `backend/src/vaakmitra/pipeline/assessment.py`
- Test: `backend/tests/integration/test_assessment_pipeline.py`
- Test: `backend/tests/unit/test_pipeline_failures.py`

**Interfaces:**
- Consumes: `AcousticModelRuntime.infer(audio, sample_rate) -> AcousticOutput`, Member 1 `AlignmentResult`, syllable definitions, vocabulary, and scoring config.
- Produces: `AssessmentPipeline.score_aligned_attempt(...) -> AssessmentResult` for Member 3.

- [ ] **Step 1: Write failing pipeline tests with a deterministic in-memory runtime**

```python
def test_pipeline_returns_traceable_phoneme_and_syllable_scores() -> None:
    pipeline = AssessmentPipeline(runtime=FixtureRuntime(), vocabulary=fixture_vocab(), config=fixture_config())
    result = pipeline.score_aligned_attempt(
        attempt_id="ATT-1",
        audio=np.zeros(3200, dtype=np.float32),
        sample_rate=16000,
        alignment=fixture_alignment(),
        syllables=(SyllableDefinition(text="அம்", phoneme_indices=(0, 1)),),
    )
    assert result.model_version == "fixture-model-1.0.0"
    assert result.vocabulary_version == "fixture-vocab-1.0.0"
    assert result.scoring_version == "fixture-gop-1.0.0"
    assert result.status == "ok"
```

- [ ] **Step 2: Run pipeline tests and verify missing-pipeline failures**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/integration/test_assessment_pipeline.py backend/tests/unit/test_pipeline_failures.py -q`

Expected: collection fails because `AssessmentPipeline` does not exist.

- [ ] **Step 3: Implement narrow orchestration and neutral error mapping**

```python
class AssessmentPipeline:
    def score_aligned_attempt(self, *, attempt_id, audio, sample_rate, alignment, syllables):
        output = self.runtime.infer(audio, sample_rate)
        validate_log_probabilities(output.log_probabilities, self.vocabulary)
        return score_alignment(
            attempt_id=attempt_id,
            output=output,
            alignment=alignment,
            syllables=syllables,
            vocabulary=self.vocabulary,
            config=self.config,
        )
```

Known validation failures map to enumerated neutral reasons; unexpected inference failures map to `model_inference_failed` without leaking exception payloads.

- [ ] **Step 4: Run focused pipeline tests and full suite**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/integration/test_assessment_pipeline.py backend/tests/unit/test_pipeline_failures.py -q`

Expected: success, low-confidence, invalid contract, and inference failure tests pass.

- [ ] **Step 5: Commit pipeline**

```powershell
git add backend/src/vaakmitra/acoustic backend/src/vaakmitra/pipeline backend/tests/integration backend/tests/unit/test_pipeline_failures.py
git commit -m "feat: orchestrate member 2 assessment scoring"
```

---

### Task 5: Model Manifest, Integrity, and ONNX Runtime

**Files:**
- Create: `backend/src/vaakmitra/acoustic/metadata.py`
- Create: `backend/src/vaakmitra/acoustic/onnx_runtime.py`
- Create: `backend/configs/model.example.json`
- Create: `modeling/artifacts/README.md`
- Test: `backend/tests/unit/test_model_metadata.py`
- Test: `backend/tests/integration/test_onnx_runtime.py`

**Interfaces:**
- Consumes: local ONNX path, `ModelManifest`, provider list, and 16 kHz float32 waveform.
- Produces: integrity-checked `OnnxAcousticModelRuntime` implementing `AcousticModelRuntime`.

- [ ] **Step 1: Write failing integrity and runtime tests**

```python
def test_manifest_rejects_tampered_model(tmp_path: Path) -> None:
    model = tmp_path / "model.onnx"
    model.write_bytes(b"tampered")
    manifest = fixture_manifest(sha256="0" * 64)
    with pytest.raises(ModelIntegrityError):
        verify_model_integrity(model, manifest)


def test_runtime_rejects_non_16khz_audio(runtime) -> None:
    with pytest.raises(ValueError, match="16000"):
        runtime.infer(np.zeros(1600, dtype=np.float32), sample_rate=8000)
```

- [ ] **Step 2: Run tests and verify expected missing-symbol failures**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_model_metadata.py backend/tests/integration/test_onnx_runtime.py -q`

Expected: collection fails for missing manifest and runtime types.

- [ ] **Step 3: Implement manifest hashing and lazy optional-runtime import**

```python
def verify_model_integrity(path: Path, manifest: ModelManifest) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if not hmac.compare_digest(digest, manifest.sha256):
        raise ModelIntegrityError("model SHA-256 does not match manifest")
```

The ONNX adapter imports `onnxruntime` only when constructed, requests explicit providers, validates one audio input and one `[batch, frames, vocabulary]` output, removes the batch dimension, and returns float32 log probabilities.

- [ ] **Step 4: Run integrity/runtime tests and full suite**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_model_metadata.py backend/tests/integration/test_onnx_runtime.py -q`

Expected: manifest tests pass; runtime tests either pass with the model-tool extra installed or are explicitly skipped for the absent optional dependency.

- [ ] **Step 5: Commit local runtime support**

```powershell
git add backend/src/vaakmitra/acoustic backend/configs/model.example.json backend/tests/unit/test_model_metadata.py backend/tests/integration/test_onnx_runtime.py modeling/artifacts/README.md
git commit -m "feat: load integrity-checked ONNX acoustic models"
```

---

### Task 6: Export, Quantization, and Benchmark Tooling

**Files:**
- Create: `modeling/export/export_onnx.py`
- Create: `modeling/quantization/quantize_onnx.py`
- Create: `modeling/validation/compare_outputs.py`
- Create: `benchmarks/run_benchmark.py`
- Create: `benchmarks/manifests/example.json`
- Test: `backend/tests/unit/test_model_tools.py`
- Test: `backend/tests/unit/test_benchmark_stats.py`

**Interfaces:**
- Consumes: explicit source checkpoint/export callable, FP32 ONNX path, calibration/fixture manifest, runtime factory, warmup count, and measured run count.
- Produces: ONNX/INT8 files, SHA-256 manifests, comparison report, and benchmark JSON with median/P95.

- [ ] **Step 1: Write failing tooling tests around pure behavior**

```python
def test_latency_summary_uses_nearest_rank_p95() -> None:
    summary = summarize_latencies([10.0, 20.0, 30.0, 40.0, 50.0])
    assert summary.median_ms == 30.0
    assert summary.p95_ms == 50.0


def test_compare_outputs_reports_max_probability_and_gop_delta() -> None:
    report = compare_outputs(fp32_fixture(), int8_fixture(), fixture_alignment())
    assert report.max_probability_delta == pytest.approx(0.02)
    assert report.max_gop_delta >= 0.0
```

- [ ] **Step 2: Run tooling tests and verify missing-function failures**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_model_tools.py backend/tests/unit/test_benchmark_stats.py -q`

Expected: collection fails because comparison and benchmark helpers do not exist.

- [ ] **Step 3: Implement explicit CLIs with prerequisite validation**

```python
def summarize_latencies(values_ms: Sequence[float]) -> LatencySummary:
    ordered = sorted(float(value) for value in values_ms)
    if not ordered or any(value < 0 or not math.isfinite(value) for value in ordered):
        raise ValueError("latencies must be finite non-negative values")
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return LatencySummary(median_ms=statistics.median(ordered), p95_ms=ordered[p95_index])
```

Export fails with a documented prerequisite error when no approved source adapter is supplied. Quantization uses ONNX Runtime's dynamic INT8 path for the transformer baseline and never overwrites the FP32 model. Benchmark JSON distinguishes laptop evidence from target-device evidence.

- [ ] **Step 4: Run tooling tests and CLI help smoke tests**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_model_tools.py backend/tests/unit/test_benchmark_stats.py -q`

Run: `.\.venv\Scripts\python.exe -m modeling.quantization.quantize_onnx --help`

Run: `.\.venv\Scripts\python.exe -m benchmarks.run_benchmark --help`

Expected: tests pass and both CLIs exit zero with usage text.

- [ ] **Step 5: Commit model tooling**

```powershell
git add modeling benchmarks backend/tests/unit/test_model_tools.py backend/tests/unit/test_benchmark_stats.py
git commit -m "feat: add edge model export and benchmark tooling"
```

---

### Task 7: Member 2 Documentation and Final Verification

**Files:**
- Create: `docs/architecture/member2-speech-intelligence.md`
- Create: `docs/contracts/member1-member2-ctc.md`
- Create: `docs/contracts/member2-member3-scoring.md`
- Create: `modeling/model_cards/ta-phoneme-ctc-baseline.md`
- Create: `benchmarks/reports/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: all implemented contracts, commands, limitations, and fresh verification output.
- Produces: integration-ready documentation and an honest model card that labels unavailable evidence as not yet measured rather than inventing results.

- [ ] **Step 1: Document exact callable and JSON contracts**

The CTC contract states `[frames, vocabulary_size]`, float32 log probabilities, explicit blank index, frame shift in milliseconds, and independent model/vocabulary versions. The scoring contract enumerates `ok`, `retry`, `unscorable`, and `error`, plus all non-sensitive reason codes.

- [ ] **Step 2: Document model provenance and evidence boundaries**

The model card identifies the AI4Bharat Tamil IndicConformer as a candidate teacher/baseline, states that the production Tamil phoneme head and therapist-labelled calibration remain required, and forbids clinical-effectiveness claims from synthetic fixtures.

- [ ] **Step 3: Run formatting and static checks**

Run: `.\.venv\Scripts\python.exe -m ruff check backend/src backend/tests modeling benchmarks`

Run: `.\.venv\Scripts\python.exe -m mypy backend/src`

Expected: both exit zero with no errors.

- [ ] **Step 4: Run the complete fresh verification suite**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests -q`

Run: `.\.venv\Scripts\python.exe -m build backend`

Expected: all tests pass and both source and wheel distributions build successfully.

- [ ] **Step 5: Audit Member 2 requirement coverage and repository cleanliness**

Run: `git diff --check`

Run: `git status --short`

Confirm M2.1 through M2.5 are represented by runtime, CTC, scoring, tooling, tests, and docs; confirm no Member 1/3 implementation or model/audio artifact is tracked.

- [ ] **Step 6: Commit documentation and verified configuration**

```powershell
git add README.md docs backend modeling benchmarks .gitignore
git commit -m "docs: complete member 2 integration guidance"
```
