from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest import mock

import pytest

NOTEBOOK = Path("notebooks/VaakMitra_GPU_Training_Colab.ipynb")


def _load_notebook() -> dict[str, Any]:
    payload: Any = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def test_colab_notebook_exposes_the_frozen_gpu_execution_contract() -> None:
    notebook = _load_notebook()

    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["accelerator"] == "GPU"
    assert notebook["metadata"]["vaakmitra_gpu_contract"] == {
        "schema_version": "1.0",
        "archive_sha256": (
            "0ec67ad6fc6b5f48aa0f2668722dbdb2642b66c4b49c289c2849ee603f35c8c2"
        ),
        "teacher_model_id": (
            "ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large"
        ),
        "teacher_revision": "8c31aa8d04964b8fc87e4eaaee7916f7d2c024da",
        "ai4bharat_nemo_revision": "8dce88cf8e94963e2033c3137f7b9993b51db88a",
        "blank_index": 0,
        "reference_stages": [
            {
                "name": "head_only",
                "encoder_learning_rate": 0.0,
                "head_learning_rate": 0.001,
            },
            {
                "name": "top_encoder_blocks",
                "top_block_count": 4,
                "encoder_learning_rate": 0.00001,
                "head_learning_rate": 0.0001,
            },
            {
                "name": "full_encoder",
                "encoder_learning_rate": 0.000001,
                "head_learning_rate": 0.00005,
                "minimum_validation_per_improvement": 0.005,
                "optional": True,
            },
        ],
        "student_architectures": ["compact_conformer", "conv_bigru"],
        "distillation_weights": {
            "supervised_phoneme_ctc": 1.0,
            "masked_smooth_l1": 0.5,
            "relational_frame_similarity": 0.2,
            "sequence_consistency": 0.1,
            "text_posterior_kl": 0.0,
        },
        "maximum_relative_student_per_degradation": 0.1,
        "default_profile": "deadline_7day",
        "checkpoint_every_updates": 500,
        "maximum_students": 1,
        "maximum_unknown_phone_record_rate": 0.05,
        "canary_seconds": 1800,
        "outputs": [
            "run-manifest.json",
            "canary-report.json",
            "reference-metrics.json",
            "reference-artifact-head-only.json",
            "reference-artifact-manifest.json",
            "teacher-feature-manifest.json",
            "student-comparison.json",
            "artifact-hashes.json",
            "vaakmitra-gpu-results.zip",
        ],
        "evidence_scope": "adult_tamil_engineering_proxy",
        "production_ready": False,
    }


def test_colab_notebook_has_ordered_resume_safe_executable_phases() -> None:
    notebook = _load_notebook()
    cells = notebook["cells"]
    cell_ids = [cell["id"] for cell in cells]

    assert cell_ids == [
        "intro",
        "configuration",
        "environment",
        "drive-and-repository",
        "shared-runtime",
        "teacher-access-and-probe",
        "corpus-materialization",
        "phoneme-targets",
        "gpu-canary",
        "reference-head-training",
        "reference-head-export",
        "reference-adaptive-training",
        "reference-final-export",
        "teacher-features",
        "student-training",
        "optional-student-export",
        "results-bundle",
    ]
    assert all(cell["cell_type"] in {"markdown", "code"} for cell in cells)
    assert all(cell.get("execution_count") is None for cell in cells if cell["cell_type"] == "code")
    assert all(cell.get("outputs") == [] for cell in cells if cell["cell_type"] == "code")

    code = "\n".join(
        "".join(cell["source"]) for cell in cells if cell["cell_type"] == "code"
    )
    assert "C:\\Users\\" not in code
    assert "HF_TOKEN = \"hf_" not in code
    assert "ALLOW_PROVISIONAL_RESEARCH_RUN" in code
    assert "attests_inventory_reviewed" in code
    assert "resume" in code.lower()
    assert "validation_per" in code
    assert "substitutions" in code
    assert "deletions" in code
    assert "insertions" in code
    assert "quantize_dynamic" in code
    assert "physical_device_required" in code
    assert 'TRAINING_PROFILE_NAME = "deadline_7day"' in code
    assert "VAAKMITRA_REPOSITORY_URL" in code
    assert "VAAKMITRA_REPOSITORY_REF" in code
    assert "shutil.disk_usage" in code
    assert "17_314_415_289" in code


def test_colab_environment_rejects_unsupported_python_before_installing() -> None:
    notebook = _load_notebook()
    environment = next(
        cell for cell in notebook["cells"] if cell["id"] == "environment"
    )
    code = "".join(environment["source"])

    fake_condacolab = SimpleNamespace(
        check=mock.Mock(side_effect=AssertionError),
        install=mock.Mock(),
    )

    with (
        mock.patch.object(sys, "version_info", (3, 13, 0, "final", 0)),
        mock.patch.dict(sys.modules, {"condacolab": fake_condacolab}),
        mock.patch("subprocess.run") as subprocess_run,
        pytest.raises(RuntimeError, match=r"2025\.07.*Python 3\.11"),
    ):
        exec(
            compile(code, "notebook:environment", "exec"),
            {
                "AI4BHARAT_NEMO_REVISION": "test-revision",
                "Path": Path,
            },
        )

    subprocess_run.assert_not_called()


def test_colab_environment_uses_the_native_python_311_runtime() -> None:
    notebook = _load_notebook()
    environment = next(
        cell for cell in notebook["cells"] if cell["id"] == "environment"
    )
    code = "".join(environment["source"])

    assert notebook["metadata"]["language_info"]["version"] == "3.11"
    assert "condacolab" not in code.lower()


def test_every_code_cell_is_valid_python() -> None:
    notebook = _load_notebook()
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), f"notebook:{cell['id']}", "exec")
