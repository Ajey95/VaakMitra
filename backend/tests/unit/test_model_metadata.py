from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from vaakmitra.acoustic.metadata import (
    ModelIntegrityError,
    ModelManifest,
    verify_model_integrity,
)


def _manifest(sha256: str) -> ModelManifest:
    return ModelManifest(
        schema_version="1.0",
        model_version="fixture-model-1.0.0",
        vocabulary_version="fixture-vocab-1.0.0",
        sha256=sha256,
        sample_rate=16000,
        frame_shift_ms=20.0,
        blank_index=0,
        vocabulary_size=3,
        input_name="audio",
        output_name="log_probabilities",
        output_kind="log_probabilities",
    )


def test_manifest_rejects_non_16khz_sample_rate() -> None:
    payload = _manifest("0" * 64).model_dump()
    payload["sample_rate"] = 8000
    with pytest.raises(ValidationError, match="16000"):
        ModelManifest.model_validate(payload)


def test_manifest_rejects_malformed_sha256() -> None:
    with pytest.raises(ValidationError, match="sha256"):
        _manifest("not-a-digest")


def test_manifest_rejects_tampered_model(tmp_path) -> None:
    model = tmp_path / "model.onnx"
    model.write_bytes(b"tampered")

    with pytest.raises(ModelIntegrityError, match="SHA-256"):
        verify_model_integrity(model, _manifest("0" * 64))


def test_manifest_accepts_matching_model_digest(tmp_path) -> None:
    model = tmp_path / "model.onnx"
    content = b"synthetic-model"
    model.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()

    verify_model_integrity(model, _manifest(digest))


def test_manifest_loads_json_contract(tmp_path) -> None:
    path = tmp_path / "manifest.json"
    payload = _manifest("0" * 64).model_dump(mode="json")
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = ModelManifest.from_json(path)

    assert loaded.model_version == "fixture-model-1.0.0"
    assert loaded.output_kind == "log_probabilities"
