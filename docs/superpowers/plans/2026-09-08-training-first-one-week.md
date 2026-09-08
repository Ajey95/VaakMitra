# Training-First One-Week Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an interruption-safe Colab pipeline that trains, evaluates, exports, and hash-binds the best available Tamil phoneme CTC reference model before spending deadline time on optional full-encoder or student runs.

**Architecture:** Pure Python modules under `modeling/training/` own profiles, deterministic batch order, resume cursors, checkpoint integrity, session budgets, and canary metrics. `notebooks/VaakMitra_GPU_Training_Colab.ipynb` remains the Colab-facing orchestrator and uses those tested modules after cloning the pinned VaakMitra commit. Google Drive holds durable manifests/checkpoints/final artifacts; corpus extraction and hot training reads use `/content`.

**Tech Stack:** Colab runtime `2025.07` with native Python 3.11, Python 3.11 local tests, PyTorch/torchaudio 2.2.0 CUDA 12.1, pinned AI4Bharat NeMo commit `8dce88cf8e94963e2033c3137f7b9993b51db88a`, Pydantic 2, NumPy 1.26, ONNX opset 17, ONNX Runtime, pytest, Ruff, strict mypy, Jupyter notebook JSON.

**Spec:** `docs/superpowers/specs/2026-09-08-training-first-one-week-design.md`

## Global Constraints

- `deadline_7day` is the default real-run profile; `smoke` and `research_full` remain available.
- OpenSLR 127 is adult Tamil engineering-proxy evidence, never child/ASD or clinical evidence.
- The expert-reviewed inventory is preferred; a provisional run must remain labelled `provisional_research_only` and must be retrained after contract changes.
- The CTC blank index is exactly `0`; unknown phones are excluded with a recorded reason and never mapped silently.
- Immutable bindings include corpus index, archive, inventory, teacher model/revision/checkpoint, configuration, and repository commit digests.
- Training checkpoints save every `500` optimizer updates, at epoch boundaries, on validation improvement, and before a time-budget stop.
- Checkpoints include model, optimizer, AMP scaler, stage, epoch, next batch, global update, sampler epoch/order inputs, best metric, history, and Python/NumPy/Torch CPU/CUDA RNG state.
- Full-encoder training is allowed only when top-block validation PER improves by at least `0.005` and its projected completion fits the remaining budget.
- Exactly one student may run in `deadline_7day`, and only after the selected reference checkpoint, test report, and export attempt are frozen.
- Audio, full transcripts, speaker identifiers, feature tensors, `.nemo`, checkpoints, and generated ONNX files remain outside Git.
- A smoke run, unexecuted notebook, or synthetic fixture is never reported as a trained model.
- Preserve the user's existing untracked documents, `output/`, and `tmp/`; stage only task-owned paths in each commit.

---

### Task 1: Deadline Profiles and Immutable Run Bindings

**Files:**
- Create: `modeling/training/deadline_profile.py`
- Create: `modeling/training/gpu/deadline-profiles.json`
- Test: `backend/tests/unit/test_deadline_profile.py`
- Modify: `backend/tests/unit/test_gpu_runbook_configs.py`

**Interfaces:**
- Consumes: profile name and checked-in JSON configuration.
- Produces: `TrainingProfileName`, `TrainingProfile`, `load_training_profile(path, name) -> TrainingProfile`, and `build_run_binding(profile, immutable_inputs) -> dict[str, object]`.

- [ ] **Step 1: Write failing tests for all three profiles and fail-closed parsing.**

```python
def test_deadline_profile_prioritizes_reference_and_one_student() -> None:
    profile = load_training_profile(PROFILES, "deadline_7day")
    assert profile.reference_epochs == {
        "head_only": 3,
        "top_encoder_blocks": 3,
        "full_encoder": 2,
    }
    assert profile.checkpoint_every_updates == 500
    assert profile.maximum_students == 1
    assert profile.session_reserve_seconds == 600
    assert profile.minimum_full_stage_per_improvement == 0.005
    assert profile.maximum_unknown_phone_record_rate == 0.05


def test_binding_changes_when_repository_commit_changes() -> None:
    profile = load_training_profile(PROFILES, "deadline_7day")
    common = {
        "archive_sha256": "1" * 64,
        "corpus_index_sha256": "2" * 64,
        "inventory_sha256": "3" * 64,
        "teacher_model_id": "ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large",
        "teacher_revision": "4" * 40,
        "teacher_checkpoint_sha256": "5" * 64,
    }
    first = build_run_binding(profile, {**common, "repository_commit": "a" * 40})
    second = build_run_binding(profile, {**common, "repository_commit": "b" * 40})
    assert first["binding_sha256"] != second["binding_sha256"]
```

- [ ] **Step 2: Run the focused tests and verify the module is missing.**

```powershell
$env:PYTHONPATH="D:\VaakMitra\backend\src;D:\VaakMitra"
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_deadline_profile.py backend/tests/unit/test_gpu_runbook_configs.py -q
```

Expected: collection fails for `modeling.training.deadline_profile`.

- [ ] **Step 3: Implement strict immutable profile models.**

```python
class TrainingProfileName(str, Enum):
    SMOKE = "smoke"
    DEADLINE_7DAY = "deadline_7day"
    RESEARCH_FULL = "research_full"


class TrainingProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: TrainingProfileName
    reference_epochs: dict[Literal["head_only", "top_encoder_blocks", "full_encoder"], int]
    student_epochs: int = Field(ge=0)
    maximum_students: int = Field(ge=0, le=2)
    batch_size: int = Field(gt=0)
    gradient_accumulation: int = Field(gt=0)
    bucket_size: int = Field(gt=0)
    checkpoint_every_updates: int = Field(gt=0)
    session_max_seconds: int = Field(gt=0)
    session_reserve_seconds: int = Field(gt=0)
    minimum_full_stage_per_improvement: float = Field(ge=0.0)
    maximum_unknown_phone_record_rate: float = Field(ge=0.0, le=1.0)
    split_limits: dict[Literal["train", "validation", "test"], int | None]
```

`load_training_profile` rejects duplicate names, missing stages, negative epochs, a reserve greater
than or equal to maximum session time, and unknown keys.

- [ ] **Step 4: Add literal checked-in profiles.**

```json
{
  "schema_version": "1.0",
  "profiles": [
    {"name": "smoke", "reference_epochs": {"head_only": 1, "top_encoder_blocks": 1, "full_encoder": 1}, "student_epochs": 1, "maximum_students": 1, "batch_size": 1, "gradient_accumulation": 1, "bucket_size": 16, "checkpoint_every_updates": 2, "session_max_seconds": 1800, "session_reserve_seconds": 120, "minimum_full_stage_per_improvement": 0.005, "maximum_unknown_phone_record_rate": 0.05, "split_limits": {"train": 64, "validation": 16, "test": 16}},
    {"name": "deadline_7day", "reference_epochs": {"head_only": 3, "top_encoder_blocks": 3, "full_encoder": 2}, "student_epochs": 5, "maximum_students": 1, "batch_size": 1, "gradient_accumulation": 8, "bucket_size": 128, "checkpoint_every_updates": 500, "session_max_seconds": 39600, "session_reserve_seconds": 600, "minimum_full_stage_per_improvement": 0.005, "maximum_unknown_phone_record_rate": 0.05, "split_limits": {"train": null, "validation": null, "test": null}},
    {"name": "research_full", "reference_epochs": {"head_only": 3, "top_encoder_blocks": 3, "full_encoder": 2}, "student_epochs": 5, "maximum_students": 2, "batch_size": 1, "gradient_accumulation": 8, "bucket_size": 128, "checkpoint_every_updates": 500, "session_max_seconds": 39600, "session_reserve_seconds": 600, "minimum_full_stage_per_improvement": 0.005, "maximum_unknown_phone_record_rate": 0.05, "split_limits": {"train": null, "validation": null, "test": null}}
  ]
}
```

- [ ] **Step 5: Implement canonical binding generation.**

```python
def build_run_binding(profile: TrainingProfile, immutable_inputs: Mapping[str, str]) -> dict[str, object]:
    required = {"archive_sha256", "corpus_index_sha256", "inventory_sha256", "teacher_model_id", "teacher_revision", "teacher_checkpoint_sha256", "repository_commit"}
    if set(immutable_inputs) != required:
        raise ValueError("immutable run-binding fields differ")
    payload: dict[str, object] = {"schema_version": "2.0", "profile": profile.model_dump(mode="json"), "inputs": dict(sorted(immutable_inputs.items())), "evidence_scope": "adult_tamil_engineering_proxy", "production_ready": False}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["binding_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload
```

- [ ] **Step 6: Run tests, Ruff, and strict mypy.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_deadline_profile.py backend/tests/unit/test_gpu_runbook_configs.py -q
& .\.venv\Scripts\python.exe -m ruff check modeling/training/deadline_profile.py backend/tests/unit/test_deadline_profile.py
& .\.venv\Scripts\python.exe -m mypy --config-file backend/pyproject.toml modeling/training/deadline_profile.py
```

- [ ] **Step 7: Commit the profile contract.**

```powershell
git add modeling/training/deadline_profile.py modeling/training/gpu/deadline-profiles.json backend/tests/unit/test_deadline_profile.py backend/tests/unit/test_gpu_runbook_configs.py
git commit -m "feat: add deadline-safe training profiles"
```

### Task 2: Deterministic Length-Bucketed Batch Order

**Files:**
- Create: `modeling/training/batch_order.py`
- Test: `backend/tests/unit/test_batch_order.py`
- Modify: `notebooks/VaakMitra_GPU_Training_Colab.ipynb` cell `phoneme-targets`

**Interfaces:**
- Consumes: immutable `LengthRecord(record_index: int, sample_count: int)` values, seed, epoch, batch size, bucket size, and next-batch cursor.
- Produces: `BatchOrder`, `build_batch_order(...) -> BatchOrder`, and `remaining_batches(order, next_batch_index) -> tuple[tuple[int, ...], ...]`.

- [ ] **Step 1: Write failing tests for determinism, bounded padding, and exact cursor slicing.**

```python
def test_resume_cursor_neither_replays_nor_skips_a_batch() -> None:
    records = tuple(LengthRecord(index, samples) for index, samples in enumerate([9, 2, 8, 1, 7, 3]))
    order = build_batch_order(records, seed=17, epoch=2, batch_size=2, bucket_size=4)
    assert order.batches[:2] + remaining_batches(order, 2) == order.batches
    assert set(chain.from_iterable(order.batches)) == set(range(6))


def test_length_bucketing_bounds_padding_inside_each_batch() -> None:
    records = tuple(LengthRecord(index, samples) for index, samples in enumerate(range(1, 17)))
    order = build_batch_order(records, seed=3, epoch=0, batch_size=2, bucket_size=4)
    sample_counts = {record.record_index: record.sample_count for record in records}
    assert all(
        max(sample_counts[index] for index in batch) - min(sample_counts[index] for index in batch) <= 3
        for batch in order.batches
    )
```

- [ ] **Step 2: Run the focused test and verify the module is missing.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_batch_order.py -q
```

- [ ] **Step 3: Implement a stable two-level shuffle.**

```python
@dataclass(frozen=True, slots=True)
class LengthRecord:
    record_index: int
    sample_count: int


@dataclass(frozen=True, slots=True)
class BatchOrder:
    seed: int
    epoch: int
    batch_size: int
    bucket_size: int
    batches: tuple[tuple[int, ...], ...]
    order_sha256: str


def build_batch_order(records: Sequence[LengthRecord], *, seed: int, epoch: int, batch_size: int, bucket_size: int) -> BatchOrder:
    if batch_size <= 0 or bucket_size < batch_size:
        raise ValueError("bucket_size must be at least batch_size")
    ordered = sorted(records, key=lambda item: (item.sample_count, item.record_index))
    buckets = [ordered[start:start + bucket_size] for start in range(0, len(ordered), bucket_size)]
    rng = random.Random(f"{seed}:{epoch}")
    for bucket in buckets:
        rng.shuffle(bucket)
    rng.shuffle(buckets)
    flattened = [item.record_index for bucket in buckets for item in bucket]
    batches = tuple(tuple(flattened[start:start + batch_size]) for start in range(0, len(flattened), batch_size))
    digest = hashlib.sha256(json.dumps(batches, separators=(",", ":")).encode()).hexdigest()
    return BatchOrder(seed, epoch, batch_size, bucket_size, batches, digest)
```

Reject duplicate or negative record indexes and non-positive sample counts. Empty records produce an
empty order. `remaining_batches` rejects negative or out-of-range cursors.

- [ ] **Step 4: Store validated duration in target-cache rows.**

The `phoneme-targets` cell copies `duration_ms` from `records.jsonl`, validates it is positive, stores
it in `TrainingItem`, and derives `sample_count = round(duration_ms * 16)` without opening each WAV
during ordering.

- [ ] **Step 5: Run tests, Ruff, and mypy.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_batch_order.py backend/tests/unit/test_openslr127.py -q
& .\.venv\Scripts\python.exe -m ruff check modeling/training/batch_order.py backend/tests/unit/test_batch_order.py
& .\.venv\Scripts\python.exe -m mypy --config-file backend/pyproject.toml modeling/training/batch_order.py
```

- [ ] **Step 6: Commit deterministic batching.**

```powershell
git add modeling/training/batch_order.py backend/tests/unit/test_batch_order.py notebooks/VaakMitra_GPU_Training_Colab.ipynb
git commit -m "feat: add deterministic length-bucketed batches"
```

### Task 3: Atomic Checkpoints and Exact Mid-Epoch Resume

**Files:**
- Create: `modeling/training/resume_checkpoint.py`
- Test: `backend/tests/unit/test_resume_checkpoint.py`

**Interfaces:**
- Consumes: model, optimizer, AMP scaler state, `ResumeCursor`, history, binding, local directory, durable directory, and RNG state.
- Produces: `ResumeCursor`, `VerifiedCheckpoint`, `capture_rng_state()`, `restore_rng_state(state)`, `save_checkpoint(...) -> VerifiedCheckpoint`, `load_checkpoint(...) -> dict[str, object]`, and `find_latest_valid_checkpoint(...) -> Path | None`.

- [ ] **Step 1: Write failing tests for cursor semantics, RNG restoration, corruption fallback, and binding rejection.**

```python
def test_mid_epoch_resume_restores_rng_and_next_unapplied_batch(tmp_path: Path) -> None:
    torch.manual_seed(9)
    model = nn.Linear(2, 1)
    optimizer = torch.optim.AdamW(model.parameters())
    cursor = ResumeCursor("head_only", 1, 7, 500, 1, "b" * 64)
    expected_random = torch.rand(3)
    torch.manual_seed(9)
    saved = save_checkpoint(
        local_dir=tmp_path / "local",
        durable_dir=tmp_path / "durable",
        binding_sha256="a" * 64,
        cursor=cursor,
        model=model,
        optimizer=optimizer,
        scaler_state={},
        best_validation_per=0.42,
        history=(),
    )
    payload = load_checkpoint(saved.durable_path, expected_binding_sha256="a" * 64)
    restore_rng_state(payload["rng_state"])
    assert payload["cursor"].next_batch_index == 7
    assert torch.equal(torch.rand(3), expected_random)
```

Add tests that truncate `last.pt`, select the newest hash-valid numbered checkpoint, and reject a
different binding before loading model state.

- [ ] **Step 2: Run the focused tests and verify the module is missing.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_resume_checkpoint.py -q
```

- [ ] **Step 3: Define the versioned cursor and verified artifact.**

```python
@dataclass(frozen=True, slots=True)
class ResumeCursor:
    stage: Literal["head_only", "top_encoder_blocks", "full_encoder", "student"]
    epoch: int
    next_batch_index: int
    global_update: int
    sampler_epoch: int
    batch_order_sha256: str


@dataclass(frozen=True, slots=True)
class VerifiedCheckpoint:
    durable_path: Path
    sha256: str
    size_bytes: int
```

Checkpoint dictionaries use `checkpoint_schema_version="2.0"`. `next_batch_index` means the next
batch whose gradients have not been applied. Save only at optimizer boundaries so partial gradient
accumulation never requires serialization.

- [ ] **Step 4: Capture and restore deterministic state.**

```python
def capture_rng_state() -> dict[str, object]:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def restore_rng_state(state: Mapping[str, object]) -> None:
    random.setstate(cast(tuple[Any, ...], state["python"]))
    np.random.set_state(cast(tuple[Any, ...], state["numpy"]))
    torch.set_rng_state(cast(torch.Tensor, state["torch_cpu"]))
    cuda_state = cast(list[torch.Tensor], state["torch_cuda"])
    if cuda_state:
        if not torch.cuda.is_available():
            raise RuntimeError("checkpoint requires CUDA RNG restoration")
        torch.cuda.set_rng_state_all(cuda_state)
```

- [ ] **Step 5: Implement atomic local-save then durable-copy verification.**

Write to `<local>/checkpoint.<pid>.tmp`, flush and `fsync`, atomically replace a numbered local file,
copy it to `<durable>/<stage>-update-000000500.pt.tmp`, verify size and SHA-256, then atomically
promote the durable file and its `.sha256.json` sidecar. Update `last.pt` only after the numbered
checkpoint verifies. Keep the previous valid checkpoint throughout.
If the durable copy fails, retain the verified local numbered checkpoint, return
`durable_checkpoint_write_failed`, and stop before another optimizer update.

- [ ] **Step 6: Implement load validation and safe fallback.**

`load_checkpoint` verifies sidecar digest, schema, binding hash, cursor values, model state, optimizer
state, scaler state, and RNG keys. `find_latest_valid_checkpoint` scans numbered checkpoints
newest-first and returns the first valid one if `last.pt` is corrupt.

- [ ] **Step 7: Run tests, Ruff, and mypy.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_resume_checkpoint.py -q
& .\.venv\Scripts\python.exe -m ruff check modeling/training/resume_checkpoint.py backend/tests/unit/test_resume_checkpoint.py
& .\.venv\Scripts\python.exe -m mypy --config-file backend/pyproject.toml modeling/training/resume_checkpoint.py
```

- [ ] **Step 8: Commit checkpoint support.**

```powershell
git add modeling/training/resume_checkpoint.py backend/tests/unit/test_resume_checkpoint.py
git commit -m "feat: add exact mid-epoch training resume"
```

### Task 4: Session Budget, Canary Metrics, and Controlled OOM Retry

**Files:**
- Create: `modeling/training/session_control.py`
- Create: `modeling/training/canary.py`
- Test: `backend/tests/unit/test_session_control.py`
- Test: `backend/tests/unit/test_training_canary.py`

**Interfaces:**
- Consumes: monotonic clock, maximum/reserve seconds, progress counters, GPU-memory readings, checkpoint timing, and stage workloads.
- Produces: `SessionBudget`, `StopDecision`, `CanaryReport`, `StageWorkload`, `project_stage_seconds(report, workload) -> float`, and `next_frame_budget_after_oom(current, retry_count) -> int`.

- [ ] **Step 1: Write failing time-budget and OOM tests.**

```python
@dataclass
class FakeClock:
    now: float

    def __call__(self) -> float:
        return self.now


def test_budget_requests_checkpoint_before_reserved_shutdown_window() -> None:
    clock = FakeClock(now=1_000.0)
    budget = SessionBudget(1_000.0, 3_600, 600, clock)
    clock.now = 4_001.0
    decision = budget.decision()
    assert decision.should_stop is True
    assert decision.reason == "session_time_budget"
    assert decision.seconds_remaining == pytest.approx(599.0)


def test_oom_budget_reduces_once_then_fails_closed() -> None:
    assert next_frame_budget_after_oom(480_000, retry_count=0) == 360_000
    with pytest.raises(RuntimeError, match="repeated CUDA out of memory"):
        next_frame_budget_after_oom(360_000, retry_count=1)
```

- [ ] **Step 2: Write failing canary projection tests.**

```python
def test_canary_projects_stage_updates() -> None:
    report = CanaryReport.from_measurements(
        elapsed_seconds=1_800.0,
        records=900,
        audio_seconds=5_400.0,
        frames=270_000,
        batches=900,
        optimizer_updates=112,
        checkpoint_seconds=18.0,
        staging_bytes=13_803_410_250,
        staging_seconds=600.0,
        peak_gpu_allocated_bytes=8_000_000_000,
        peak_gpu_reserved_bytes=9_000_000_000,
        peak_host_rss_bytes=4_000_000_000,
        environment={"gpu": "fixture"},
    )
    assert report.optimizer_updates_per_minute == pytest.approx(112 / 30)
    assert project_stage_seconds(report, StageWorkload(optimizer_updates=1_120)) == pytest.approx(18_000)
```

- [ ] **Step 3: Run focused tests and verify both modules are missing.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_session_control.py backend/tests/unit/test_training_canary.py -q
```

- [ ] **Step 4: Implement fail-closed session controls.**

`SessionBudget.decision()` uses an injected monotonic clock. A system-clock change cannot extend a
session. `next_frame_budget_after_oom` performs exactly one 25% reduction. The caller empties the
CUDA cache and resumes from the last verified optimizer-boundary checkpoint.

- [ ] **Step 5: Implement a privacy-safe canary report.**

```python
class CanaryReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1.0"] = "1.0"
    elapsed_seconds: float = Field(gt=0)
    records: int = Field(gt=0)
    audio_seconds: float = Field(gt=0)
    frames: int = Field(gt=0)
    batches: int = Field(gt=0)
    optimizer_updates: int = Field(gt=0)
    checkpoint_seconds: float = Field(ge=0)
    staging_bytes: int = Field(ge=0)
    staging_seconds: float = Field(ge=0)
    staging_mib_per_second: float = Field(ge=0)
    records_per_minute: float = Field(gt=0)
    audio_seconds_per_second: float = Field(gt=0)
    optimizer_updates_per_minute: float = Field(gt=0)
    peak_gpu_allocated_bytes: int = Field(ge=0)
    peak_gpu_reserved_bytes: int = Field(ge=0)
    peak_host_rss_bytes: int = Field(ge=0)
    environment: dict[str, str | int | bool | None]
    evidence_scope: Literal["throughput_projection_not_model_quality"] = "throughput_projection_not_model_quality"
```

Serialization rejects paths, audio, transcripts, speaker/utterance IDs, environment variables, and
token-shaped values.

- [ ] **Step 6: Run tests, Ruff, and mypy.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_session_control.py backend/tests/unit/test_training_canary.py -q
& .\.venv\Scripts\python.exe -m ruff check modeling/training/session_control.py modeling/training/canary.py backend/tests/unit/test_session_control.py backend/tests/unit/test_training_canary.py
& .\.venv\Scripts\python.exe -m mypy --config-file backend/pyproject.toml modeling/training/session_control.py modeling/training/canary.py
```

- [ ] **Step 7: Commit session controls.**

```powershell
git add modeling/training/session_control.py modeling/training/canary.py backend/tests/unit/test_session_control.py backend/tests/unit/test_training_canary.py
git commit -m "feat: add GPU canary and session controls"
```

### Task 5: Resumable Reference-Stage Engine

**Files:**
- Create: `modeling/training/reference_stage.py`
- Test: `backend/tests/unit/test_reference_stage.py`
- Modify: `backend/tests/unit/test_training_stages.py`
- Modify: `backend/tests/integration/test_full_track_cpu_smoke.py`
- Modify: `modeling/training/smoke_full_track.py`

**Interfaces:**
- Consumes: model, stage configuration, `BatchOrder`, checkpoint paths, `SessionBudget`, evaluation callback, and CTC batch callback.
- Produces: `StageResult`, `GateDecision`, `run_reference_stage(...) -> StageResult`, `run_fixture_reference(...) -> StageResult`, `should_run_top_stage(...) -> GateDecision`, and `should_run_full_stage(...) -> GateDecision`.

- [ ] **Step 1: Write a failing integration test that interrupts and resumes mid-epoch.**

```python
def test_resumed_fixture_training_matches_uninterrupted_weights(tmp_path: Path) -> None:
    uninterrupted = run_fixture_reference(seed=17, epochs=2, stop_after_updates=None, root=tmp_path / "a")
    stopped = run_fixture_reference(seed=17, epochs=2, stop_after_updates=2, root=tmp_path / "b")
    assert stopped.status == "checkpointed_for_session_stop"
    resumed = run_fixture_reference(seed=17, epochs=2, stop_after_updates=None, root=tmp_path / "b")
    assert resumed.status == "complete"
    assert resumed.global_updates == uninterrupted.global_updates
    assert_state_dict_equal(resumed.model_state, uninterrupted.model_state)
```

- [ ] **Step 2: Write failing stage-gate tests.**

```python
def test_full_stage_requires_metric_and_time_budget() -> None:
    allowed = should_run_full_stage(0.40, 0.39, 0.005, 7_200, 8_000)
    denied = should_run_full_stage(0.40, 0.399, 0.005, 7_200, 8_000)
    assert allowed.allowed is True
    assert denied == GateDecision(False, "validation_per_improvement_below_0.005")
```

Also test non-finite PER, insufficient time, missing reloadable head checkpoint, and top-stage
admission after a complete head result.

- [ ] **Step 3: Run focused tests and verify the engine interfaces are missing.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_reference_stage.py backend/tests/integration/test_full_track_cpu_smoke.py -q
```

- [ ] **Step 4: Implement optimizer-boundary cursor updates.**

The engine performs these exact operations:

1. Build the deterministic order for `cursor.epoch`.
2. Verify `cursor.batch_order_sha256` before a non-zero resume.
3. Start at `cursor.next_batch_index`.
4. Accumulate exactly `gradient_accumulation` compatible batches, or the final partial group.
5. Clip gradients, call scaler step/update, zero gradients, increment `global_update`, and set
   `next_batch_index` to the first unapplied batch.
6. Check the session budget and checkpoint interval only after that boundary.
7. Save before returning `checkpointed_for_session_stop`.
8. Evaluate after a completed epoch, update best PER/history, save epoch/best checkpoints, then
   advance to the next epoch at batch zero.

Every controlled stop also atomically writes `run-status.json` with binding hash, stage, cursor,
reason, latest verified checkpoint hash, elapsed seconds, and `production_ready=false`.

- [ ] **Step 5: Preserve head-only encoder inference behavior.**

For `head_only`, keep `model.acoustic.eval()` while the phoneme head trains. Use the existing stage
learning rates and final-four-block invariant. Keep `modeling.training.stages` imports backward
compatible if the shared enum or gates move to `reference_stage.py`.

- [ ] **Step 6: Persist privacy-safe diagnostic failures.**

For non-finite loss or gradients, write binding hash, cursor, scalar loss, gradient-norm summary,
stage, environment versions, and failure code. Exclude batch items, audio paths, target sequences,
transcripts, logits, and hidden states.

- [ ] **Step 7: Update CPU smoke to exercise stop/save/resume.**

Extend `FullTrackSmokeReport` with `checkpoint_schema_version`, `mid_epoch_resume_verified`, and
`final_state_sha256`. Preserve `evidence_scope="fixture_encoder_shapes_only"`,
`upstream_checkpoint_loaded=False`, and `cuda_training_completed=False`.

- [ ] **Step 8: Run stage, smoke, and existing CTC tests.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_reference_stage.py backend/tests/unit/test_training_stages.py backend/tests/unit/test_phoneme_head.py backend/tests/integration/test_full_track_cpu_smoke.py -q
& .\.venv\Scripts\python.exe -m ruff check modeling/training/reference_stage.py modeling/training/smoke_full_track.py backend/tests/unit/test_reference_stage.py
& .\.venv\Scripts\python.exe -m mypy --config-file backend/pyproject.toml modeling/training/reference_stage.py modeling/training/smoke_full_track.py
```

- [ ] **Step 9: Commit the reference engine.**

```powershell
git add modeling/training/reference_stage.py modeling/training/smoke_full_track.py backend/tests/unit/test_reference_stage.py backend/tests/unit/test_training_stages.py backend/tests/integration/test_full_track_cpu_smoke.py
git commit -m "feat: make reference training interruption-safe"
```

### Task 6: Reference Artifact Export and Evidence Freezing

**Files:**
- Create: `modeling/export/reference_artifact.py`
- Test: `backend/tests/unit/test_reference_artifact.py`
- Modify: `modeling/export/export_onnx.py`
- Modify: `backend/tests/integration/test_dual_track_onnx.py`

**Interfaces:**
- Consumes: selected native checkpoint, reference model wrapper, ordered tokens, sample rate, frame metadata, run binding, validation/test metrics, and fixed one-second audio fixture.
- Produces: `ReferenceArtifactManifest`, `ReferenceExportResult`, `export_reference_candidate(...) -> ReferenceExportResult`, and `freeze_reference_evidence(...) -> Path`.

- [ ] **Step 1: Write failing tests that preserve native artifacts when ONNX export fails.**

```python
def test_export_failure_still_freezes_native_reference_manifest(tmp_path: Path) -> None:
    class UnsupportedFixtureModel(nn.Module):
        def forward(self, audio: torch.Tensor, lengths: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            raise RuntimeError("unsupported fixture export")

    native_checkpoint = tmp_path / "selected.pt"
    native_checkpoint.write_bytes(b"fixture checkpoint")
    validation_metrics = tmp_path / "validation.json"
    validation_metrics.write_text('{"phoneme_error_rate":0.4}\n', encoding="utf-8")
    result = export_reference_candidate(
        model=UnsupportedFixtureModel(),
        native_checkpoint=native_checkpoint,
        output_dir=tmp_path / "out",
        tokens=("<blank>", "a"),
        run_binding={"binding_sha256": "a" * 64},
        artifact_role="head_only_candidate",
        selected_stage="head_only",
        validation_metrics_path=validation_metrics,
        test_metrics_path=None,
        sample_rate_hz=16_000,
        frame_subsampling=4,
    )
    assert result.native_checkpoint_preserved is True
    assert result.onnx_status == "failed"
    assert result.failure_report_path is not None
    assert result.failure_report_path.is_file()
```

Add a success test that loads generated ONNX with ONNX Runtime and compares output shape, frame
lengths, and finite-value statistics against PyTorch for one- and two-second fixtures.

- [ ] **Step 2: Run focused tests and verify the new module is missing.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_reference_artifact.py backend/tests/integration/test_dual_track_onnx.py -q
```

- [ ] **Step 3: Implement a strict reference manifest.**

```python
class ReferenceArtifactManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["1.0"] = "1.0"
    binding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_role: Literal["head_only_candidate", "selected_reference"]
    selected_stage: Literal["head_only", "top_encoder_blocks", "full_encoder"]
    checkpoint: ArtifactRecord
    onnx: ArtifactRecord | None
    onnx_status: Literal["passed", "failed"]
    onnx_failure_report: ArtifactRecord | None
    vocabulary: tuple[str, ...]
    blank_index: Literal[0] = 0
    sample_rate_hz: Literal[16000] = 16000
    frame_subsampling: int = Field(gt=0)
    validation_metrics_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    test_metrics_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence_scope: Literal["adult_tamil_engineering_proxy"] = "adult_tamil_engineering_proxy"
    production_ready: Literal[False] = False
```

- [ ] **Step 4: Export the reference before feature extraction.**

Wrap the model to return `logits` and `frame_lengths`, export opset 17 with dynamic axes, validate
with `onnx.checker`, and run ONNX Runtime parity. Invoke it immediately after head-only validation as
`head_only_candidate`, without touching the test split, and again after final selection as
`selected_reference`. Validate that only `selected_reference` may carry `test_metrics_sha256`.
Catch errors only around export; write exception class, sanitized message, operator diagnostics,
environment and checkpoint digest to `reference-export-failure.json`, then continue with the native
checkpoint.

- [ ] **Step 5: Freeze validation/test evidence once.**

Use exclusive creation for the selected test report. Hash stage histories, selected checkpoint,
vocabulary, run manifest, validation report, test report, export result, and environment. Evaluate
the frozen test set only after reference selection.

- [ ] **Step 6: Run tests, Ruff, and mypy.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_reference_artifact.py backend/tests/integration/test_dual_track_onnx.py backend/tests/unit/test_model_parity.py -q
& .\.venv\Scripts\python.exe -m ruff check modeling/export/reference_artifact.py modeling/export/export_onnx.py backend/tests/unit/test_reference_artifact.py
& .\.venv\Scripts\python.exe -m mypy --config-file backend/pyproject.toml modeling/export/reference_artifact.py modeling/export/export_onnx.py
```

- [ ] **Step 7: Commit reference export.**

```powershell
git add modeling/export/reference_artifact.py modeling/export/export_onnx.py backend/tests/unit/test_reference_artifact.py backend/tests/integration/test_dual_track_onnx.py
git commit -m "feat: freeze reference model artifacts"
```

### Task 7: Rewire the Colab Notebook as the Deadline Orchestrator

**Files:**
- Modify: `notebooks/VaakMitra_GPU_Training_Colab.ipynb` cells `intro`, `configuration`, `drive-and-repository`, `shared-runtime`, `corpus-materialization`, `phoneme-targets`, `reference-training`, `teacher-features`, `student-training`, `evaluation-export`, and `results-bundle`; split reference work into the new phase IDs below
- Modify: `backend/tests/unit/test_gpu_colab_notebook.py`
- Create: `backend/tests/integration/test_deadline_notebook_static.py`

**Interfaces:**
- Consumes: checked-in profile JSON and Tasks 1-6 modules from the exact repository commit recorded by the run.
- Produces: ordered notebook phases, `canary-report.json`, durable reference checkpoints, `reference-metrics.json`, `reference-artifact-manifest.json`, optional one-student evidence, `artifact-hashes.json`, and `vaakmitra-gpu-results.zip`.

- [ ] **Step 1: Write failing notebook contract tests.**

```python
def test_deadline_notebook_runs_canary_before_reference_training() -> None:
    notebook = _load_notebook()
    ids = [cell["id"] for cell in notebook["cells"]]
    assert ids.index("gpu-canary") < ids.index("reference-head-training")
    contract = notebook["metadata"]["vaakmitra_gpu_contract"]
    assert contract["default_profile"] == "deadline_7day"
    assert contract["checkpoint_every_updates"] == 500


def test_deadline_notebook_exports_reference_before_student_work() -> None:
    ids = [cell["id"] for cell in _load_notebook()["cells"]]
    assert ids.index("reference-head-training") < ids.index("reference-head-export")
    assert ids.index("reference-head-export") < ids.index("reference-adaptive-training")
    assert ids.index("reference-final-export") < ids.index("teacher-features")
```

The static integration test also requires imports of `resume_checkpoint`, `batch_order`,
`session_control`, `canary`, and `reference_artifact`; `maximum_students == 1` for the deadline
profile; and no test-set evaluation before final reference selection.

- [ ] **Step 2: Run notebook tests and verify the new assertions fail.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_gpu_colab_notebook.py backend/tests/integration/test_deadline_notebook_static.py -q
```

- [ ] **Step 3: Make the notebook run a pinned repository revision.**

Add `VAAKMITRA_REPOSITORY_URL`, `VAAKMITRA_REPOSITORY_REF`, and
`TRAINING_PROFILE_NAME="deadline_7day"` to configuration. Clone/fetch under
`/content/vaakmitra-source`, resolve the configured ref to a commit, checkout that commit detached,
add it to `sys.path`, load `deadline-profiles.json`, and record the resolved 40-character commit.
Stop on a dirty checkout or notebook/module training-contract version mismatch.

- [ ] **Step 4: Stage hot data locally and verify capacity.**

Before copying the 13,803,410,250-byte archive, call `shutil.disk_usage("/content")` and require
archive bytes plus `17_314_415_289` extracted bytes plus a 10 GiB working reserve. Copy from Drive
to `.part`, verify size/SHA-256, and atomically promote. Retain the safe tar-member and pair-count
checks.

- [ ] **Step 5: Replace notebook shuffling and checkpointing with tested modules.**

Create `LengthRecord`s from cached durations, build `BatchOrder` per epoch, load the newest verified
compatible cursor, and call the reference engine. Durable files remain under
`DRIVE_PRIVATE/reference/<stage>/`; temporary files use `WORK_ROOT/checkpoints/<stage>/`.
Reject the run before training when `unknown_or_unreviewed_phone / total_eligible_records` exceeds
the profile's `maximum_unknown_phone_record_rate` of `0.05`.

- [ ] **Step 6: Add the `gpu-canary` cell.**

Run the same model, autocast, batch order, collation, gradient accumulation, optimizer, and
checkpoint manager used by head-only for `CANARY_SECONDS=1800`. Restore starting head weights after
the throughput probe, then force stop/save/reload/one-update resume. Write `canary-report.json` and
stage projections. Stop if resume, finite-loss, staging-throughput, or checkpoint verification fails.

- [ ] **Step 7: Gate and reorder expensive phases.**

```text
configuration -> environment -> drive/repository -> shared runtime -> teacher probe
-> corpus materialization -> phoneme targets -> GPU canary -> reference-head-training
-> reference-head-export -> reference-adaptive-training -> reference-final-export
-> optional teacher features -> optional one-student training
-> optional student export -> results bundle
```

Head-only is mandatory and produces `reference-artifact-head-only.json` before another stage starts.
Top blocks require a reloadable head checkpoint and a canary projection that fits. Full encoder
requires time fit and the `0.005` PER gate. Final selection produces
`reference-artifact-manifest.json`. `deadline_7day` selects
`compact_conformer` as its one student and records `conv_bigru` as `deferred_by_deadline_profile`.

- [ ] **Step 8: Make result bundling accept skipped optional phases.**

Always require run manifest, teacher probe, canary report, reference metrics, head-only reference
manifest, final reference artifact manifest, and artifact hashes. Include teacher-feature/student
files only when complete. Use final
status `complete_adult_tamil_reference_evidence` without a student and
`complete_adult_tamil_reference_and_student_evidence` with one; both keep
`production_ready=false`.

- [ ] **Step 9: Keep notebook JSON clean and portable.**

Set code-cell execution counts to `null`, outputs to empty, and preserve format 4. Reject Windows
absolute paths and inline token-shaped values. Preserve existing archive, teacher, blank-index,
evidence-scope, and safety metadata while adding deadline fields.

- [ ] **Step 10: Run notebook and training-control tests.**

```powershell
& .\.venv\Scripts\python.exe -m json.tool notebooks/VaakMitra_GPU_Training_Colab.ipynb > $null
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_gpu_colab_notebook.py backend/tests/integration/test_deadline_notebook_static.py backend/tests/unit/test_deadline_profile.py backend/tests/unit/test_batch_order.py backend/tests/unit/test_resume_checkpoint.py backend/tests/unit/test_session_control.py backend/tests/unit/test_training_canary.py backend/tests/unit/test_reference_stage.py backend/tests/unit/test_reference_artifact.py backend/tests/integration/test_full_track_cpu_smoke.py -q
```

- [ ] **Step 11: Commit the orchestrator.**

```powershell
git add notebooks/VaakMitra_GPU_Training_Colab.ipynb backend/tests/unit/test_gpu_colab_notebook.py backend/tests/integration/test_deadline_notebook_static.py
git commit -m "feat: prioritize resumable reference training in Colab"
```

### Task 8: Runbook, Complete Local Verification, and Colab Launch Handoff

**Files:**
- Modify: `modeling/training/gpu/README.md`
- Modify: `modeling/training/README.md`
- Modify: `README.md`
- Create: `docs/verification/training-first-colab-preflight.md`
- Test: `backend/tests/unit/test_training_first_docs.py`

**Interfaces:**
- Consumes: verified notebook/profile, private metadata bundle, OpenSLR archive, accepted gated-model access, and a Colab GPU runtime.
- Produces: exact launch/reconnect instructions, canary decision worksheet, artifact checklist, and evidence boundary.

- [ ] **Step 1: Write a failing documentation contract test.**

```python
def test_runbook_contains_deadline_launch_and_recovery_commands() -> None:
    text = Path("modeling/training/gpu/README.md").read_text(encoding="utf-8")
    assert 'TRAINING_PROFILE_NAME="deadline_7day"' in text
    assert "canary-report.json" in text
    assert "checkpoint every 500 optimizer updates" in text
    assert "rerun from the configuration cell" in text
    assert "adult Tamil engineering proxy" in text
    assert "not child or clinical validation" in text
```

- [ ] **Step 2: Run the documentation test and verify deadline instructions are missing.**

```powershell
& .\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_training_first_docs.py -q
```

- [ ] **Step 3: Document exact preflight and launch actions.**

The operator must:

1. Upload `modeling/artifacts/colab/vaakmitra-colab-private-metadata.zip` to
   `/content/drive/MyDrive/VaakMitraGPU/inputs/`.
2. Upload or permit download of `mile_tamil_asr_corpus.tar.gz` and verify pinned size/SHA-256.
3. Accept AI4Bharat model conditions and place `HF_TOKEN` only in Colab Secrets.
4. Select a GPU runtime, confirm the repository ref, execute from configuration, and verify the
   resolved commit printed by the repository cell.
5. Confirm the environment cell reports Python 3.11, the pinned PyTorch version, and the assigned GPU.
6. Inspect `canary-report.json` before the long stage.
7. After preemption, reconnect and rerun from configuration; compatible checkpoints resume at the
   next unapplied optimizer boundary.
8. Download the result ZIP and selected native checkpoint separately because native weights stay
   outside the public evidence bundle.

- [ ] **Step 4: Add a concrete preflight evidence table.**

```markdown
| Gate | Required value |
|---|---|
| Notebook commit | exact 40-character Git commit recorded in run manifest |
| GPU | detected and recorded; no guaranteed model assumed |
| Canary duration | at least 1,800 seconds unless smoke profile |
| Mid-epoch resume | passed |
| Non-finite loss | zero events |
| Head-only projected finish | fits remaining deadline budget |
| Inventory | expert reviewed, or provisional research-only flag recorded |
| Evidence ceiling | adult Tamil engineering proxy; production ready false |
```

- [ ] **Step 5: Run complete local verification.**

```powershell
$env:PYTHONPATH="D:\VaakMitra\backend\src;D:\VaakMitra"
& .\.venv\Scripts\python.exe -m pytest backend/tests -q
& .\.venv\Scripts\python.exe -m ruff check backend/src backend/tests modeling
& .\.venv\Scripts\python.exe -m mypy --config-file backend/pyproject.toml backend/src modeling
& .\.venv\Scripts\python.exe -m json.tool notebooks/VaakMitra_GPU_Training_Colab.ipynb > $null
git diff --check
```

Expected: pytest passes; Ruff, mypy, notebook parsing, and Git whitespace checks exit `0`.

- [ ] **Step 6: Run CPU smoke twice and compare state digests.**

```powershell
& .\.venv\Scripts\python.exe -m modeling.training.smoke_full_track --seed 17 --steps 3 --output modeling/artifacts/smoke/full-track-a.json
& .\.venv\Scripts\python.exe -m modeling.training.smoke_full_track --seed 17 --steps 3 --output modeling/artifacts/smoke/full-track-b.json
```

Both reports must state `mid_epoch_resume_verified=true`, remain fixture-only evidence, and contain
matching deterministic training-state digests.

- [ ] **Step 7: Commit runbook and verification documentation.**

```powershell
git add README.md modeling/training/README.md modeling/training/gpu/README.md docs/verification/training-first-colab-preflight.md backend/tests/unit/test_training_first_docs.py
git commit -m "docs: add training-first Colab runbook"
```

- [ ] **Step 8: Perform the real Colab canary and record verified external evidence.**

Open the committed notebook in Colab Pro, execute through `gpu-canary`, and copy the resulting
`canary-report.json` plus sanitized status under ignored `modeling/artifacts/gpu/`. Do not claim the
canary or training completed until those files and matching Drive checkpoint hashes are inspected.
Use measured updates per minute to continue on the assigned GPU or move to persistent compute.
