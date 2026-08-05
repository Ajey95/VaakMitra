# Mobile Readiness Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert ONNX Runtime mobile-checker output into reproducible structured evidence and record the current proxy model's CPU-only recommendation without misrepresenting it as a device benchmark.

**Architecture:** A pure parser converts checker text into a frozen report, while a CLI subprocess wrapper executes the official ONNX Runtime module against a hash-identified local model. Static compatibility evidence is separate from existing latency benchmarks.

**Tech Stack:** Python 3.11, Pydantic 2, ONNX Runtime tooling, pytest, Ruff, mypy, build.

## Global Constraints

- Static graph analysis is never labelled a real-device benchmark.
- Emulator measurements do not satisfy physical-device acceptance.
- The current model must recommend `CPUExecutionProvider` when NNAPI suitability is `NO`.
- Reports include model hash and size but no local absolute path.
- Subprocess failures expose neutral stable error codes, not environment paths.
- All code changes use red-green-refactor.

---

### Task 1: Parse mobile usability output

**Files:**
- Create: `modeling/mobile/__init__.py`
- Create: `modeling/mobile/usability_audit.py`
- Test: `backend/tests/unit/test_mobile_usability_audit.py`

**Interfaces:**
- Consumes: `parse_mobile_checker_output(text: str, model_sha256: str, model_size_bytes: int) -> MobileUsabilityReport`.
- Produces: structured NNAPI node/partition counts, unsupported operators, dynamic-shape status, and provider recommendation.

- [ ] **Step 1: Write a failing parser test using representative official output**

```python
def test_parser_recommends_cpu_when_nnapi_is_not_suitable() -> None:
    report = parse_mobile_checker_output(CHECKER_OUTPUT, "a" * 64, 48679)
    assert report.evidence_scope == "static_mobile_compatibility_audit"
    assert report.nnapi.supported_nodes == 8
    assert report.nnapi.total_nodes == 51
    assert report.nnapi.partition_count == 5
    assert report.recommended_execution_provider == "CPUExecutionProvider"
    assert "ai.onnx:GRU" in report.nnapi.unsupported_operators
```

- [ ] **Step 2: Run the test and confirm missing-module failure**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_mobile_usability_audit.py -q`

- [ ] **Step 3: Implement strict parsing and validation**

Parse `N/M nodes`, partition sizes, unsupported-operator lines, dynamic-shape counts, and final recommendations. Reject missing NNAPI sections, inconsistent node totals, invalid SHA-256, non-positive file size, or unknown final recommendation. Set `physical_device_measured=false` unconditionally.

- [ ] **Step 4: Run focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_mobile_usability_audit.py -q`

- [ ] **Step 5: Commit the parser**

```powershell
git add -- modeling/mobile backend/tests/unit/test_mobile_usability_audit.py
git commit -m "feat: parse ONNX mobile usability evidence"
```

### Task 2: Execute and persist the current model audit

**Files:**
- Modify: `modeling/mobile/usability_audit.py`
- Create: `benchmarks/reports/proxy-int8-mobile-usability.json`
- Test: `backend/tests/integration/test_mobile_usability_cli.py`

**Interfaces:**
- Consumes: `audit_mobile_usability(model_path: Path) -> MobileUsabilityReport` and CLI arguments `--model`, `--output`.
- Produces: deterministic JSON containing only filename, size, SHA-256, parsed graph support, and evidence limitations.

- [ ] **Step 1: Write a failing integration test with a stubbed checker command**

```python
def test_audit_writes_static_evidence_without_absolute_path(tmp_path: Path, monkeypatch) -> None:
    model = tmp_path / "model.onnx"
    model.write_bytes(b"fixture")
    monkeypatch.setattr(usability_audit, "_run_checker", lambda _: CHECKER_OUTPUT)
    report = audit_mobile_usability(model)
    payload = report.model_dump(mode="json")
    assert payload["model_filename"] == "model.onnx"
    assert str(tmp_path) not in json.dumps(payload)
    assert payload["physical_device_measured"] is False
```

- [ ] **Step 2: Run the integration test and confirm failure**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/integration/test_mobile_usability_cli.py -q`

- [ ] **Step 3: Implement subprocess execution and atomic report writing**

Run `[sys.executable, "-m", "onnxruntime.tools.check_onnx_model_mobile_usability", str(model)]`, capture merged stdout/stderr, reject non-zero exit as `RuntimeError("mobile_usability_checker_failed")`, and write UTF-8 JSON only when the destination does not already exist.

- [ ] **Step 4: Generate the current proxy report**

Run:

```powershell
.\.venv\Scripts\python.exe -m modeling.mobile.usability_audit `
  --model modeling/artifacts/proxy-trained-small-v1/ta-proxy-phone-ctc-int8.onnx `
  --output benchmarks/reports/proxy-int8-mobile-usability.json
```

Expected: CPU execution provider recommended; NNAPI as-is support records 8 of 51 nodes across 5 partitions.

- [ ] **Step 5: Run focused tests and verify report content**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_mobile_usability_audit.py backend/tests/integration/test_mobile_usability_cli.py -q`

- [ ] **Step 6: Commit CLI and report**

```powershell
git add -- modeling/mobile/usability_audit.py backend/tests/integration/test_mobile_usability_cli.py benchmarks/reports/proxy-int8-mobile-usability.json
git commit -m "bench: record ONNX mobile readiness audit"
```

### Task 3: Final documentation and repository verification

**Files:**
- Modify: `docs/verification/member2-completion-report.md`
- Modify: `benchmarks/reports/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: all mocked integration, alternative-strategy, and mobile-audit outputs.
- Produces: updated evidence map and final verification record.

- [ ] **Step 1: Update documentation with current outcomes**

Record the mock-only three-member flow, provisional inventory tooling, teacher-feature boundary, licensed source preflight, and static mobile audit. Keep real Member 1 alignment, real Member 3 integration, therapist calibration, model accuracy, and physical-device testing as open gates.

- [ ] **Step 2: Run all tests**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests -q`

- [ ] **Step 3: Run lint and strict type checks**

Run: `.\.venv\Scripts\python.exe -m ruff check backend modeling benchmarks`

Run: `.\.venv\Scripts\python.exe -m mypy backend/src modeling benchmarks`

- [ ] **Step 4: Build the backend package and check CLIs**

Run: `.\.venv\Scripts\python.exe -m build backend`

Run the `--help` command for the mocked pipeline, inventory generator, and mobile audit modules.

- [ ] **Step 5: Check the final diff and secret/large-file boundaries**

Run: `git diff --check`

Run: `git status --short`

Verify no generated audio, feature arrays, model weights, credentials, or files larger than 5 MB are staged.

- [ ] **Step 6: Commit final documentation**

```powershell
git add -- README.md benchmarks/reports/README.md docs/verification/member2-completion-report.md
git commit -m "docs: record mocked integration and strategy evidence"
```
