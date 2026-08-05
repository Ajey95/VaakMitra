"""Build a deterministic tiny CTC ONNX graph for engineering smoke tests only."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from modeling.artifacts import ArtifactRecord, describe_artifact


def create_synthetic_ctc_model(output_path: str | Path) -> ArtifactRecord:
    """Create a quantizable one-frame fixture; it is not a trained Tamil model."""

    output = Path(output_path)
    if output.exists():
        raise ValueError("synthetic model output exists; refusing to overwrite")
    try:
        import onnx
        from onnx import TensorProto, helper, numpy_helper
    except ImportError as error:
        raise RuntimeError("onnx model extra is required for fixture generation") from error

    audio_input = helper.make_tensor_value_info("audio", TensorProto.FLOAT, [1, 4])
    log_probability_output = helper.make_tensor_value_info(
        "log_probabilities",
        TensorProto.FLOAT,
        [1, 1, 3],
    )
    weights = numpy_helper.from_array(
        np.array(
            [
                [-0.2, 0.4, 0.1],
                [-0.1, -0.2, 0.3],
                [0.1, 0.5, -0.3],
                [0.0, 0.1, 0.2],
            ],
            dtype=np.float32,
        ),
        name="ctc_weight",
    )
    axes = numpy_helper.from_array(np.array([1], dtype=np.int64), name="frame_axis")
    nodes = [
        helper.make_node("MatMul", ["audio", "ctc_weight"], ["logits"]),
        helper.make_node("Unsqueeze", ["logits", "frame_axis"], ["framed_logits"]),
        helper.make_node(
            "LogSoftmax",
            ["framed_logits"],
            ["log_probabilities"],
            axis=2,
        ),
    ]
    graph = helper.make_graph(
        nodes,
        "vaakmitra-synthetic-ctc-fixture",
        [audio_input],
        [log_probability_output],
        initializer=[weights, axes],
    )
    model = helper.make_model(
        graph,
        producer_name="vaakmitra-member2-fixture",
        opset_imports=[helper.make_opsetid("", 17)],
    )
    onnx.checker.check_model(model)
    output.parent.mkdir(parents=True, exist_ok=True)
    onnx.save_model(model, output)
    return describe_artifact(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a deterministic synthetic CTC ONNX smoke-test model."
    )
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(create_synthetic_ctc_model(args.output).as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

