"""DEC-040 / PHN-006: metrics must describe the exact frozen ONNX replay."""

import copy

import pytest


def evidence():
    manifest = {
        "model_file": "phoneme.fp32.onnx",
        "checkpoint_sha256": "cp",
        "dataset_sha256": "data",
        "model_sha256": "onnx",
        "decoder": {"type": "greedy"},
    }
    measured = {
        "all": {"phoneme_error_rate": 0.59, "records": 1665},
        "target19": {"phoneme_error_rate": 0.13889, "records": 107},
    }
    report = {
        "chosen": "fp32",
        "metrics": {
            "fp32": measured,
            "int8": {
                **measured,
                "target19": {"phoneme_error_rate": 0.14259, "records": 107},
            },
        },
    }
    return manifest, copy.deepcopy(report), measured


@pytest.mark.parametrize(
    "field",
    [
        "chosen",
        "metrics",
        "checkpoint_sha256",
        "dataset_sha256",
        "model_sha256",
        "decoder",
    ],
)
def test_dec040_export_gate_rejects_mismatched_artifact_or_metrics(field):
    from scripts.model.select_phoneme_improvement import validate_export_evaluation

    manifest, report, measured = evidence()
    validate_export_evaluation(
        manifest, report, measured, "cp", "data", "onnx", {"type": "greedy"}
    )
    if field == "chosen":
        report[field] = "int8"
    elif field == "metrics":
        report[field]["fp32"]["all"]["phoneme_error_rate"] = 0.58
    else:
        manifest[field] = "changed"
    with pytest.raises(ValueError):
        validate_export_evaluation(
            manifest, report, measured, "cp", "data", "onnx", {"type": "greedy"}
        )
