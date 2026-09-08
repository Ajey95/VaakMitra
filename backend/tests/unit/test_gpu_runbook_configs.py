from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, cast

GPU_DIR = Path("modeling/training/gpu")
MODEL_ID = "ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large"
MODEL_REVISION = "8c31aa8d04964b8fc87e4eaaee7916f7d2c024da"
NEMO_REVISION = "8dce88cf8e94963e2033c3137f7b9993b51db88a"


def _config(name: str) -> dict[str, Any]:
    payload: Any = json.loads((GPU_DIR / name).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def test_environment_pins_compatible_python_cuda_torch_and_ai4bharat_nemo() -> None:
    environment = _config("environment.yaml")

    assert environment["channels"] == ["pytorch", "nvidia", "conda-forge"]
    dependencies = environment["dependencies"]
    assert "python=3.10.12" in dependencies
    assert "pytorch=2.2.0" in dependencies
    assert "pytorch-cuda=12.1" in dependencies
    assert environment["ai4bharat_nemo"] == {
        "repository": "https://github.com/AI4Bharat/NeMo.git",
        "revision": NEMO_REVISION,
        "install_extra": "asr",
    }


def test_local_model_tooling_keeps_numpy_compatible_with_python_311_mypy() -> None:
    project = tomllib.loads(Path("backend/pyproject.toml").read_text(encoding="utf-8"))
    requirements = Path("modeling/training/requirements-cpu.txt").read_text(
        encoding="utf-8"
    )

    assert "numpy>=1.26,<2" in project["project"]["dependencies"]
    assert "numpy==1.26.4" in requirements.splitlines()
    assert project["tool"]["mypy"]["exclude"] == ["^modeling/artifacts/"]
    assert "overrides" not in project["tool"]["mypy"]


def test_full_reference_has_exact_staged_transfer_schedule_and_fail_closed_inputs() -> None:
    config = _config("full-reference.yaml")

    assert config["teacher"] == {"model_id": MODEL_ID, "revision": MODEL_REVISION}
    assert config["blank_index"] == 0
    assert config["required_inputs"] == {
        "reviewed_inventory_path": "REQUIRED_PATH",
        "reviewed_inventory_sha256": "REQUIRED_64_HEX",
        "archive_sha256": "REQUIRED_64_HEX",
        "frozen_corpus_index_path": "REQUIRED_PATH",
        "frozen_corpus_index_sha256": "REQUIRED_64_HEX",
    }
    assert config["stages"] == [
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
            "requires_validation_improvement": True,
        },
    ]
    assert config["precision"] == {"primary": "bf16-mixed", "fallback": "16-mixed"}
    assert config["gradient_clip_norm"] == 1.0
    assert config["seed"] == 17
    assert config["checkpoints"]["resume_safe"] is True
    assert config["checkpoints"]["save_top_k"] == 3
    assert config["promotion"]["metric"] == "validation_per"
    assert config["promotion"]["minimum_absolute_improvement"] == 0.005


def test_student_configs_share_teacher_features_and_edge_gates() -> None:
    conformer = _config("student-conformer.yaml")
    conv_bigru = _config("student-conv-bigru.yaml")

    assert conformer["architecture"] == "compact_conformer"
    assert conv_bigru["architecture"] == "conv_bigru"
    for config in (conformer, conv_bigru):
        assert config["blank_index"] == 0
        assert config["teacher_feature_manifest_sha256"] == "REQUIRED_64_HEX"
        assert config["objectives"] == {
            "supervised_phoneme_ctc": {"weight": 1.0},
            "masked_smooth_l1": {"weight": 0.5},
            "relational_frame_similarity": {"weight": 0.2},
            "sequence_consistency": {"weight": 0.1},
            "text_posterior_kl": {"enabled": False, "prohibited": True},
        }
        assert config["edge_gates"]["maximum_quantized_bytes"] == 50_000_000
        assert config["edge_gates"]["maximum_physical_tablet_p95_ms"] == 500
        assert config["selection"]["metric"] == "adult_proxy_test_per"
        assert config["selection"]["maximum_relative_teacher_per_degradation"] == 0.10
        assert config["production_ready"] is False


def test_deadline_profiles_prioritize_reference_and_limit_students() -> None:
    config = _config("deadline-profiles.json")
    profiles = {profile["name"]: profile for profile in config["profiles"]}

    assert set(profiles) == {"smoke", "deadline_7day", "research_full"}
    deadline = profiles["deadline_7day"]
    assert deadline["checkpoint_every_updates"] == 500
    assert deadline["maximum_students"] == 1
    assert deadline["minimum_full_stage_per_improvement"] == 0.005
    assert deadline["maximum_unknown_phone_record_rate"] == 0.05


def test_powershell_scripts_are_fail_closed_and_never_accept_tokens_as_arguments() -> None:
    stages = (GPU_DIR / "run_stages.ps1").read_text(encoding="utf-8")
    distillation = (GPU_DIR / "run_distillation.ps1").read_text(encoding="utf-8")

    for script in (stages, distillation):
        assert "HF_TOKEN" not in script
        assert "REQUIRED_64_HEX" in script
        assert "Get-FileHash" in script
        assert "torch.cuda.is_available" in script
        assert "throw" in script
    assert "head_only" in stages
    assert "top_encoder_blocks" in stages
    assert "full_encoder" in stages
    assert "student-conformer.yaml" in distillation
    assert "student-conv-bigru.yaml" in distillation
