from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from modeling.mobile import usability_audit

CHECKER_OUTPUT = """
INFO: Checking NNAPI
INFO: 5 partitions with a total of 8/51 nodes can be handled by the NNAPI EP.
INFO: Partition sizes: [1, 1, 1, 4, 1]
INFO: Unsupported nodes due to operator=14
INFO: Unsupported ops: ai.onnx:ConstantOfShape,ai.onnx:ConvInteger,ai.onnx:GRU
INFO: Unsupported nodes due to input having a dynamic shape=42
INFO: Model should perform well with NNAPI as is: NO
INFO: Checking if model will perform better if the dynamic shapes are fixed...
INFO: 10 partitions with a total of 37/51 nodes can be handled by the NNAPI EP.
INFO: Partition sizes: [1, 5, 3, 5, 3, 5, 4, 4, 3, 4]
INFO: Unsupported nodes due to operator=14
INFO: Unsupported ops: ai.onnx:ConstantOfShape,ai.onnx:ConvInteger,ai.onnx:GRU
INFO: Model should perform well with NNAPI if modified to have fixed input shapes: NO
INFO: Checking CoreML NeuralNetwork
INFO: For optimal performance the model should be used with the CPU EP.
"""


def test_audit_uses_hash_and_filename_without_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.onnx"
    model.write_bytes(b"fixture")
    monkeypatch.setattr(usability_audit, "_run_checker", lambda _: CHECKER_OUTPUT)

    report = usability_audit.audit_mobile_usability(model)
    payload = report.model_dump(mode="json")

    assert payload["model_filename"] == "model.onnx"
    assert payload["model_sha256"] == hashlib.sha256(b"fixture").hexdigest()
    assert payload["model_size_bytes"] == 7
    assert str(tmp_path) not in json.dumps(payload)
    assert payload["physical_device_measured"] is False


def test_cli_writes_utf8_json_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.onnx"
    output = tmp_path / "report.json"
    model.write_bytes(b"fixture")
    monkeypatch.setattr(usability_audit, "_run_checker", lambda _: CHECKER_OUTPUT)

    assert usability_audit.main(["--model", str(model), "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["recommended_execution_provider"] == "CPUExecutionProvider"

    with pytest.raises(FileExistsError):
        usability_audit.main(["--model", str(model), "--output", str(output)])


def test_audit_rejects_missing_or_empty_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(usability_audit, "_run_checker", lambda _: CHECKER_OUTPUT)
    with pytest.raises(ValueError, match="non-empty"):
        usability_audit.audit_mobile_usability(tmp_path / "missing.onnx")
    empty = tmp_path / "empty.onnx"
    empty.touch()
    with pytest.raises(ValueError, match="non-empty"):
        usability_audit.audit_mobile_usability(empty)


def test_checker_failure_uses_stable_error_without_output_or_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.onnx"
    model.write_bytes(b"fixture")

    class FailedProcess:
        returncode = 1
        stdout = "failure at C:/private/model.onnx"
        stderr = "stack trace"

    monkeypatch.setattr(usability_audit.subprocess, "run", lambda *args, **kwargs: FailedProcess())

    with pytest.raises(RuntimeError) as error:
        usability_audit._run_checker(model)
    assert str(error.value) == "mobile_usability_checker_failed"
