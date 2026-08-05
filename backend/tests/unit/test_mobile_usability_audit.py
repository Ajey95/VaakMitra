from __future__ import annotations

import pytest
from modeling.mobile.usability_audit import parse_mobile_checker_output
from pydantic import ValidationError

CHECKER_OUTPUT = """
INFO: Checking NNAPI
INFO: 5 partitions with a total of 8/51 nodes can be handled by the NNAPI EP.
INFO: Partition sizes: [1, 1, 1, 4, 1]
INFO: Unsupported nodes due to operator=14
INFO: Unsupported ops: ai.onnx:ConstantOfShape,ai.onnx:ConvInteger,
INFO: ai.onnx:DynamicQuantizeLinear,ai.onnx:Erf,ai.onnx:
GRU,ai.onnx:MatMulInteger,ai.onnx:Shape
INFO: Unsupported nodes due to input having a dynamic shape=42
INFO: Model should perform well with NNAPI as is: NO
INFO: --------
INFO: Checking if model will perform better if the dynamic shapes are fixed...
INFO: Partition information if the model was updated to make the shapes fixed:
INFO: 10 partitions with a total of 37/51 nodes can be handled by the NNAPI EP.
INFO: Partition sizes: [1, 5, 3, 5, 3, 5, 4, 4, 3, 4]
INFO: Unsupported nodes due to operator=14
INFO: Unsupported ops: ai.onnx:ConstantOfShape,ai.onnx:ConvInteger,
INFO: ai.onnx:DynamicQuantizeLinear,ai.onnx:Erf,ai.onnx:
GRU,ai.onnx:MatMulInteger,ai.onnx:Shape
INFO: Model should perform well with NNAPI if modified to have fixed input shapes: NO
INFO: ================
INFO: Checking CoreML NeuralNetwork
INFO: For optimal performance the model should be used with the CPU EP.
"""


def test_parser_recommends_cpu_when_nnapi_is_not_suitable() -> None:
    report = parse_mobile_checker_output(CHECKER_OUTPUT, "a" * 64, 48_679)

    assert report.evidence_scope == "static_mobile_compatibility_audit"
    assert report.nnapi.supported_nodes == 8
    assert report.nnapi.total_nodes == 51
    assert report.nnapi.partition_count == 5
    assert report.nnapi.partition_sizes == (1, 1, 1, 4, 1)
    assert report.nnapi.dynamic_shape_node_count == 42
    assert report.nnapi.fixed_shape_supported_nodes == 37
    assert report.nnapi.fixed_shape_partition_count == 10
    assert report.nnapi.suitable_as_is is False
    assert report.nnapi.suitable_with_fixed_shapes is False
    assert report.recommended_execution_provider == "CPUExecutionProvider"
    assert "ai.onnx:GRU" in report.nnapi.unsupported_operators
    assert report.physical_device_measured is False


@pytest.mark.parametrize("digest", ["bad", "A" * 64, "a" * 63])
def test_parser_rejects_invalid_model_digest(digest: str) -> None:
    with pytest.raises(ValidationError):
        parse_mobile_checker_output(CHECKER_OUTPUT, digest, 48_679)


def test_parser_rejects_non_positive_model_size() -> None:
    with pytest.raises(ValidationError):
        parse_mobile_checker_output(CHECKER_OUTPUT, "a" * 64, 0)


def test_parser_rejects_missing_nnapi_section() -> None:
    with pytest.raises(ValueError, match="NNAPI"):
        parse_mobile_checker_output(
            "For optimal performance the model should be used with the CPU EP.",
            "a" * 64,
            1,
        )


def test_parser_rejects_inconsistent_partition_sizes() -> None:
    output = CHECKER_OUTPUT.replace("[1, 1, 1, 4, 1]", "[1, 1]")

    with pytest.raises(ValidationError, match="partition sizes"):
        parse_mobile_checker_output(output, "a" * 64, 48_679)


def test_parser_rejects_unknown_provider_recommendation() -> None:
    output = CHECKER_OUTPUT.replace(
        "For optimal performance the model should be used with the CPU EP.",
        "No provider recommendation was produced.",
    )

    with pytest.raises(ValueError, match="recommendation"):
        parse_mobile_checker_output(output, "a" * 64, 48_679)
