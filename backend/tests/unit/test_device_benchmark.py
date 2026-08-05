from __future__ import annotations

import json
from pathlib import Path

import pytest
from modeling.mobile.device_benchmark import (
    DeviceBenchmarkInput,
    percentile,
    validate_device_benchmark,
)
from modeling.mobile.parse_device_report import main
from pydantic import ValidationError


def _input(**overrides: object) -> DeviceBenchmarkInput:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "service": "aws_device_farm",
        "service_run_id": "run-123",
        "device_fingerprint": "vendor/tablet/device:14/release",
        "device_model": "Representative Android Tablet",
        "android_api": 34,
        "form_factor": "tablet",
        "is_physical": True,
        "execution_provider": "CPUExecutionProvider",
        "repetitions": 30,
        "cold_load_ms": 120.0,
        "latency_samples_ms": [100.0 + index for index in range(30)],
        "peak_memory_mb": 80.0,
        "thermal_status": "nominal",
        "model_sha256": "a" * 64,
        "offline_assertion": True,
        "network_access_detected": False,
        "fixture_scope": "synthetic_non_sensitive",
    }
    payload.update(overrides)
    return DeviceBenchmarkInput.model_validate(payload)


def test_percentile_uses_linear_interpolation() -> None:
    assert percentile((1.0, 2.0, 3.0, 4.0), 0.5) == pytest.approx(2.5)
    assert percentile((1.0, 2.0, 3.0, 4.0), 0.95) == pytest.approx(3.85)


def test_physical_offline_report_computes_metrics_and_passes_boundary() -> None:
    report = validate_device_benchmark(_input(), expected_model_sha256="a" * 64)

    assert report.median_latency_ms == pytest.approx(114.5)
    assert report.p95_latency_ms == pytest.approx(127.55)
    assert report.physical_device_measured is True
    assert report.offline_verified is True
    assert report.promotable is True


def test_emulator_or_network_access_cannot_satisfy_device_gate() -> None:
    emulator = validate_device_benchmark(
        _input(is_physical=False), expected_model_sha256="a" * 64
    )
    networked = validate_device_benchmark(
        _input(network_access_detected=True), expected_model_sha256="a" * 64
    )

    assert emulator.promotable is False
    assert emulator.physical_device_measured is False
    assert networked.promotable is False
    assert networked.offline_verified is False


def test_model_digest_mismatch_blocks_report() -> None:
    with pytest.raises(ValueError, match="model digest"):
        validate_device_benchmark(_input(), expected_model_sha256="b" * 64)


def test_input_rejects_insufficient_repetitions_and_private_fields() -> None:
    with pytest.raises(ValidationError, match="repetitions"):
        _input(repetitions=2, latency_samples_ms=[1.0, 2.0])
    payload = _input().model_dump(mode="json")
    payload["transcript"] = "private"
    with pytest.raises(ValidationError, match="transcript"):
        DeviceBenchmarkInput.model_validate(payload)


def test_device_report_cli_writes_aggregate_metrics(tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output.json"
    input_path.write_text(_input().model_dump_json(), encoding="utf-8")

    assert (
        main(
            [
                "--input",
                str(input_path),
                "--expected-model-sha256",
                "a" * 64,
                "--output",
                str(output_path),
            ]
        )
        == 0
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["promotable"] is True
    assert "latency_samples_ms" not in payload
