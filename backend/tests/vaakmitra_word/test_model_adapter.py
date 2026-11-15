from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from app.vaakmitra_word.model import (
    ModelCapabilityError,
    NeMoIndicConformerAdapter,
    sha256_file,
)


def test_sha256_file_matches_bytes(tmp_path: Path) -> None:
    artifact = tmp_path / "model.nemo"
    artifact.write_bytes(b"model fixture")

    assert sha256_file(artifact) == hashlib.sha256(b"model fixture").hexdigest()


def test_hash_mismatch_prevents_model_load(tmp_path: Path) -> None:
    artifact = tmp_path / "model.nemo"
    artifact.write_bytes(b"model fixture")
    adapter = NeMoIndicConformerAdapter(
        model_path=artifact,
        expected_sha256="0" * 64,
    )

    with pytest.raises(ModelCapabilityError, match="integrity"):
        adapter.load()

    assert adapter.ready is False


def test_missing_model_has_typed_capability_error(tmp_path: Path) -> None:
    adapter = NeMoIndicConformerAdapter(
        model_path=tmp_path / "missing.nemo",
        expected_sha256="0" * 64,
    )

    with pytest.raises(ModelCapabilityError, match="unavailable"):
        adapter.load()


def test_prv002_infer_uses_tamil_in_memory_audio_without_wav_files(tmp_path: Path) -> None:
    class AI4BharatModelDouble:
        def __init__(self) -> None:
            self.audio_samples = None
            self.cur_decoder = "rnnt"
            self.training = True

        def eval(self):
            self.training = False

        def transcribe(
            self,
            paths: list[np.ndarray],
            *,
            batch_size: int,
            logprobs: bool,
            language_id: str,
        ) -> list[str]:
            assert batch_size == 1
            assert logprobs is False
            assert language_id == "ta"
            assert len(paths) == 1
            assert not self.training
            assert isinstance(paths[0], np.ndarray)
            self.audio_samples = paths[0]
            self.training = True  # Pinned NeMo unfreezes submodules on transcription teardown.
            return ["அம்மா"]

    adapter = NeMoIndicConformerAdapter(
        model_path=tmp_path / "not-loaded.nemo",
        expected_sha256="0" * 64,
    )
    model = AI4BharatModelDouble()
    adapter._model = model
    adapter._encode = lambda samples: np.ones((2, 3), dtype=np.float32)

    evidence = adapter.infer(np.zeros(1600, dtype=np.float32), 16000, "அம்மா")

    assert evidence.candidates[0].word == "அம்மா"
    assert evidence.target_probability == 1.0
    assert evidence.model_version == "ai4bharat-indicconformer-ta-hybrid-ctc-rnnt-large:ctc:ta"
    assert model.cur_decoder == "ctc"
    assert np.array_equal(model.audio_samples, np.zeros(1600, dtype=np.float32))
    assert model.training is False


def test_infer_extracts_nested_ai4bharat_transcription_result(tmp_path: Path) -> None:
    class AI4BharatNestedResultDouble:
        cur_decoder = "rnnt"

        def eval(self):
            pass

        def transcribe(
            self,
            paths: list[str],
            *,
            batch_size: int,
            logprobs: bool,
            language_id: str,
        ) -> tuple[list[str], None]:
            return (["தமிழ்"], None)

    adapter = NeMoIndicConformerAdapter(
        model_path=tmp_path / "not-loaded.nemo",
        expected_sha256="0" * 64,
    )
    adapter._model = AI4BharatNestedResultDouble()
    adapter._encode = lambda samples: np.ones((2, 3), dtype=np.float32)

    evidence = adapter.infer(np.zeros(1600, dtype=np.float32), 16000, "தமிழ்")

    assert evidence.candidates[0].word == "தமிழ்"
    assert evidence.target_probability == 1.0
