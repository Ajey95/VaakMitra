from __future__ import annotations

import hashlib

import numpy as np
import pytest
from modeling.export.export_onnx import ExportPrerequisiteError, export_with_adapter
from modeling.quantization.quantize_onnx import validate_quantization_paths
from modeling.validation.compare_outputs import compare_probability_outputs

from vaakmitra.contracts.alignment import AlignedPhoneme
from vaakmitra.ctc.vocabulary import PhonemeVocabulary


def test_compare_outputs_reports_probability_and_gop_delta() -> None:
    fp32 = np.log(
        np.array(
            [
                [0.05, 0.80, 0.15],
                [0.05, 0.75, 0.20],
            ],
            dtype=np.float64,
        )
    )
    int8 = np.log(
        np.array(
            [
                [0.05, 0.78, 0.17],
                [0.05, 0.73, 0.22],
            ],
            dtype=np.float64,
        )
    )
    aligned = (
        AlignedPhoneme(
            phoneme="a",
            start_frame=0,
            end_frame=2,
            start_ms=0.0,
            end_ms=40.0,
            confidence=0.9,
        ),
    )
    vocabulary = PhonemeVocabulary("fixture-vocab-1", ("<blank>", "a", "m"))

    report = compare_probability_outputs(fp32, int8, aligned, vocabulary)

    assert report.max_probability_delta == pytest.approx(0.02)
    assert report.mean_probability_delta == pytest.approx(0.013333333333333334)
    assert report.max_gop_delta > 0.0


def test_compare_outputs_requires_identical_shapes() -> None:
    vocabulary = PhonemeVocabulary("fixture-vocab-1", ("<blank>", "a", "m"))

    with pytest.raises(ValueError, match="identical shapes"):
        compare_probability_outputs(
            np.zeros((2, 3)),
            np.zeros((3, 3)),
            (),
            vocabulary,
        )


def test_quantization_never_overwrites_source_model(tmp_path) -> None:
    model = tmp_path / "model.onnx"
    model.write_bytes(b"model")

    with pytest.raises(ValueError, match="different"):
        validate_quantization_paths(model, model)


def test_export_adapter_must_create_nonempty_onnx_file(tmp_path) -> None:
    checkpoint = tmp_path / "teacher.nemo"
    checkpoint.write_bytes(b"checkpoint")
    output = tmp_path / "model.onnx"

    def broken_adapter(checkpoint_path, output_path) -> None:
        del checkpoint_path, output_path

    with pytest.raises(ExportPrerequisiteError, match="non-empty"):
        export_with_adapter(broken_adapter, checkpoint, output)


def test_export_adapter_returns_digest_for_created_model(tmp_path) -> None:
    checkpoint = tmp_path / "teacher.nemo"
    checkpoint.write_bytes(b"checkpoint")
    output = tmp_path / "model.onnx"

    def fixture_adapter(checkpoint_path, output_path) -> None:
        assert checkpoint_path == checkpoint
        output_path.write_bytes(b"onnx-fixture")

    record = export_with_adapter(fixture_adapter, checkpoint, output)

    assert record.size_bytes == len(b"onnx-fixture")
    assert record.sha256 == hashlib.sha256(b"onnx-fixture").hexdigest()
