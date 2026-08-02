from __future__ import annotations

import hashlib

import numpy as np
import onnx
import pytest
from onnx import TensorProto, helper, numpy_helper

from vaakmitra.acoustic.metadata import ModelManifest
from vaakmitra.acoustic.onnx_runtime import (
    ModelRuntimeConfigurationError,
    OnnxAcousticModelRuntime,
)


def _create_constant_model(path) -> np.ndarray:
    probabilities = np.array(
        [[0.05, 0.85, 0.10], [0.05, 0.15, 0.80]],
        dtype=np.float32,
    )
    log_probabilities = np.log(probabilities)[None, :, :]
    audio_input = helper.make_tensor_value_info("audio", TensorProto.FLOAT, [1, "samples"])
    output = helper.make_tensor_value_info(
        "log_probabilities",
        TensorProto.FLOAT,
        [1, 2, 3],
    )
    constant = helper.make_node(
        "Constant",
        inputs=[],
        outputs=["log_probabilities"],
        value=numpy_helper.from_array(log_probabilities),
    )
    graph = helper.make_graph([constant], "fixture-ctc", [audio_input], [output])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    onnx.save(model, path)
    return log_probabilities[0]


def _manifest(path) -> ModelManifest:
    return ModelManifest(
        schema_version="1.0",
        model_version="fixture-model-1.0.0",
        vocabulary_version="fixture-vocab-1.0.0",
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        sample_rate=16000,
        frame_shift_ms=20.0,
        blank_index=0,
        vocabulary_size=3,
        input_name="audio",
        output_name="log_probabilities",
        output_kind="log_probabilities",
    )


def test_runtime_loads_integrity_checked_local_model(tmp_path) -> None:
    path = tmp_path / "fixture.onnx"
    expected = _create_constant_model(path)
    runtime = OnnxAcousticModelRuntime(path, _manifest(path))

    output = runtime.infer(np.zeros(1600, dtype=np.float32), sample_rate=16000)

    np.testing.assert_allclose(output.log_probabilities, expected, atol=1e-6)
    assert output.model_version == "fixture-model-1.0.0"
    assert output.log_probabilities.shape == (2, 3)


def test_runtime_rejects_non_16khz_audio(tmp_path) -> None:
    path = tmp_path / "fixture.onnx"
    _create_constant_model(path)
    runtime = OnnxAcousticModelRuntime(path, _manifest(path))

    with pytest.raises(ValueError, match="16000"):
        runtime.infer(np.zeros(1600, dtype=np.float32), sample_rate=8000)


def test_runtime_rejects_unavailable_execution_provider(tmp_path) -> None:
    path = tmp_path / "fixture.onnx"
    _create_constant_model(path)

    with pytest.raises(ModelRuntimeConfigurationError, match="provider"):
        OnnxAcousticModelRuntime(
            path,
            _manifest(path),
            providers=("ImaginaryExecutionProvider",),
        )
