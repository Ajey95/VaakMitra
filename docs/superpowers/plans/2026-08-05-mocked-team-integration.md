# Mocked Team Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build explicit test-only Member 1 and Member 3 adapters and a privacy-safe mocked three-member evidence flow around the existing Member 2 pipeline.

**Architecture:** Mock adapters live under `modeling/team_mocks` and consume or produce the existing frozen Pydantic contracts. Production code under `backend/src/vaakmitra` remains unchanged. A runner assembles deterministic synthetic acoustic evidence, mock alignment, real Member 2 scoring, and a mock action into a hash-linked non-production JSON report.

**Tech Stack:** Python 3.11, NumPy, Pydantic 2, pytest, existing VaakMitra contracts and scoring pipeline.

## Global Constraints

- Every mock output must declare `evidence_scope="mock_dependency_integration"`, `production_eligible=false`, and `clinical_validity=false`.
- Mock code must remain outside `backend/src/vaakmitra`.
- No output may contain audio, embeddings, frame probabilities, transcripts, or identity.
- Unknown, low-confidence, and invalid evidence must remain neutral.
- All production changes follow red-green-refactor test-driven development.

---

### Task 1: Deterministic Member 1 alignment adapter

**Files:**
- Create: `modeling/team_mocks/__init__.py`
- Create: `modeling/team_mocks/member1_alignment.py`
- Test: `backend/tests/unit/test_member1_alignment_mock.py`

**Interfaces:**
- Consumes: `expected_phonemes: tuple[str, ...]`, `frame_count: int`, `frame_shift_ms: float`, and `confidence: float`.
- Produces: `MockAlignmentEnvelope` and `build_mock_alignment(...) -> MockAlignmentEnvelope`.

- [ ] **Step 1: Write failing tests for deterministic partitioning and impossible allocation**

```python
def test_mock_alignment_partitions_every_frame_without_overlap() -> None:
    envelope = build_mock_alignment(("a", "m", "aː"), 8, 20.0, confidence=0.9)
    assert envelope.alignment.status == "valid"
    assert [(p.start_frame, p.end_frame) for p in envelope.alignment.phonemes] == [
        (0, 3), (3, 6), (6, 8)
    ]
    assert envelope.evidence_scope == "mock_dependency_integration"
    assert envelope.production_eligible is False


def test_mock_alignment_returns_neutral_invalid_when_frames_are_insufficient() -> None:
    envelope = build_mock_alignment(("a", "m", "aː"), 2, 20.0, confidence=0.9)
    assert envelope.alignment.status == "invalid"
    assert envelope.alignment.reason == "mock_insufficient_frames"
```

- [ ] **Step 2: Run tests and verify the missing-module failure**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_member1_alignment_mock.py -q`

Expected: FAIL because `modeling.team_mocks.member1_alignment` does not exist.

- [ ] **Step 3: Implement immutable metadata and balanced half-open partitions**

```python
@dataclass(frozen=True, slots=True)
class MockAlignmentEnvelope:
    dependency: str
    implementation: str
    evidence_scope: str
    production_eligible: bool
    clinical_validity: bool
    alignment: AlignmentResult


def build_mock_alignment(
    expected_phonemes: tuple[str, ...],
    frame_count: int,
    frame_shift_ms: float,
    *,
    confidence: float,
) -> MockAlignmentEnvelope:
    if not expected_phonemes:
        raise ValueError("expected_phonemes must be non-empty")
    if frame_count < len(expected_phonemes):
        return _envelope(AlignmentResult(
            status="invalid", confidence=0.0, reason="mock_insufficient_frames"
        ))
    bounds = tuple((i * frame_count) // len(expected_phonemes) for i in range(len(expected_phonemes) + 1))
    phonemes = tuple(
        AlignedPhoneme(
            phoneme=phoneme,
            start_frame=bounds[index],
            end_frame=bounds[index + 1],
            start_ms=bounds[index] * frame_shift_ms,
            end_ms=bounds[index + 1] * frame_shift_ms,
            confidence=confidence,
        )
        for index, phoneme in enumerate(expected_phonemes)
    )
    return _envelope(AlignmentResult(status="valid", confidence=confidence, phonemes=phonemes))
```

- [ ] **Step 4: Run the focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_member1_alignment_mock.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the Member 1 mock**

```powershell
git add -- modeling/team_mocks/__init__.py modeling/team_mocks/member1_alignment.py backend/tests/unit/test_member1_alignment_mock.py
git commit -m "test: add explicit member 1 alignment mock"
```

### Task 2: Deterministic Member 3 action adapter

**Files:**
- Create: `modeling/team_mocks/member3_actions.py`
- Test: `backend/tests/unit/test_member3_action_mock.py`

**Interfaces:**
- Consumes: `AssessmentResult`.
- Produces: `MockActionEnvelope` and `choose_mock_action(result: AssessmentResult) -> MockActionEnvelope`.

- [ ] **Step 1: Write failing tests for safe action mapping**

```python
@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("retry", "ENCOURAGE_NEUTRAL_RETRY"),
        ("unscorable", "REQUEST_NEUTRAL_RECAPTURE"),
        ("error", "PAUSE_AND_REPORT_TECHNICAL_ERROR"),
    ],
)
def test_mock_action_preserves_neutral_failures(status: str, expected: str) -> None:
    action = choose_mock_action(assessment_fixture(status=status))
    assert action.response_intent == expected
    assert action.clinical_validity is False
```

Add separate fixtures proving all-pass maps to `CELEBRATE_AND_CONTINUE` and a coach unit maps to `ENCOURAGE_TARGETED_PRACTICE` with only the lowest-scoring usable unit selected.

- [ ] **Step 2: Run tests and verify the missing-module failure**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_member3_action_mock.py -q`

Expected: FAIL because `modeling.team_mocks.member3_actions` does not exist.

- [ ] **Step 3: Implement the immutable action envelope and mapping**

```python
ResponseIntent = Literal[
    "CELEBRATE_AND_CONTINUE",
    "ENCOURAGE_TARGETED_PRACTICE",
    "ENCOURAGE_NEUTRAL_RETRY",
    "REQUEST_NEUTRAL_RECAPTURE",
    "PAUSE_AND_REPORT_TECHNICAL_ERROR",
]


@dataclass(frozen=True, slots=True)
class MockActionEnvelope:
    dependency: str
    implementation: str
    evidence_scope: str
    production_eligible: bool
    clinical_validity: bool
    response_intent: ResponseIntent
    weak_unit: str | None


def choose_mock_action(result: AssessmentResult) -> MockActionEnvelope:
    if result.status == "error":
        return _action("PAUSE_AND_REPORT_TECHNICAL_ERROR")
    if result.status == "unscorable":
        return _action("REQUEST_NEUTRAL_RECAPTURE")
    if result.status == "retry":
        return _action("ENCOURAGE_NEUTRAL_RETRY")
    coached = tuple(score for score in result.phoneme_scores if score.status == "coach")
    if coached:
        weakest = min(coached, key=lambda score: (score.gop, score.phoneme))
        return _action("ENCOURAGE_TARGETED_PRACTICE", weak_unit=weakest.phoneme)
    return _action("CELEBRATE_AND_CONTINUE")
```

- [ ] **Step 4: Run the focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_member3_action_mock.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the Member 3 mock**

```powershell
git add -- modeling/team_mocks/member3_actions.py backend/tests/unit/test_member3_action_mock.py
git commit -m "test: add explicit member 3 action mock"
```

### Task 3: Mocked three-member evidence runner

**Files:**
- Create: `modeling/team_mocks/run_mocked_pipeline.py`
- Test: `backend/tests/integration/test_mocked_three_member_pipeline.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `run_mocked_pipeline(report_path: Path) -> MockedPipelineReport`.
- Produces: a JSON-compatible report with `release_status="technical_prototype"` and `evidence_scope="mocked_three_member_pipeline"`.

- [ ] **Step 1: Write a failing integration test**

```python
def test_mocked_team_flow_is_complete_private_and_non_production(tmp_path: Path) -> None:
    report = run_mocked_pipeline(tmp_path / "report.json")
    payload = report.as_dict()
    assert payload["evidence_scope"] == "mocked_three_member_pipeline"
    assert payload["release_status"] == "technical_prototype"
    assert payload["production_eligible"] is False
    serialized = json.dumps(payload)
    for forbidden in ("audio", "log_probabilities", "embedding", "transcript"):
        assert forbidden not in serialized
```

- [ ] **Step 2: Run the test and verify the missing-runner failure**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/integration/test_mocked_three_member_pipeline.py -q`

Expected: FAIL because the runner does not exist.

- [ ] **Step 3: Implement the runner using the existing synthetic runtime pattern**

Use a deterministic in-memory `AcousticModelRuntime`, call `AssessmentPipeline.infer`, create alignment with `build_mock_alignment`, call `score_aligned_attempt`, and pass its result to `choose_mock_action`. Hash the canonical JSON payload with SHA-256 and write with UTF-8 only after verifying the destination does not exist.

- [ ] **Step 4: Run focused and full mocked-flow tests**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_member1_alignment_mock.py backend/tests/unit/test_member3_action_mock.py backend/tests/integration/test_mocked_three_member_pipeline.py -q`

Expected: PASS.

- [ ] **Step 5: Document the mock-only execution command**

Add to `README.md`:

```powershell
.\.venv\Scripts\python.exe -m modeling.team_mocks.run_mocked_pipeline `
  --report benchmarks/reports/member2-mocked-three-member-evidence.json
```

State directly that this validates contract plumbing only.

- [ ] **Step 6: Commit the mocked flow**

```powershell
git add -- modeling/team_mocks/run_mocked_pipeline.py backend/tests/integration/test_mocked_three_member_pipeline.py README.md
git commit -m "test: exercise mocked three-member pipeline"
```
