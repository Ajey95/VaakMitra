from __future__ import annotations

import json
from pathlib import Path

import pytest
from modeling.training.deadline_profile import (
    TrainingProfileName,
    build_run_binding,
    load_training_profile,
)

PROFILES = Path("modeling/training/gpu/deadline-profiles.json")


def _immutable_inputs(*, repository_commit: str = "a" * 40) -> dict[str, str]:
    return {
        "archive_sha256": "1" * 64,
        "corpus_index_sha256": "2" * 64,
        "inventory_sha256": "3" * 64,
        "teacher_model_id": "ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large",
        "teacher_revision": "4" * 40,
        "teacher_checkpoint_sha256": "5" * 64,
        "repository_commit": repository_commit,
    }


def test_deadline_profile_prioritizes_reference_and_one_student() -> None:
    profile = load_training_profile(PROFILES, "deadline_7day")

    assert profile.name is TrainingProfileName.DEADLINE_7DAY
    assert profile.reference_epochs == {
        "head_only": 3,
        "top_encoder_blocks": 3,
        "full_encoder": 2,
    }
    assert profile.checkpoint_every_updates == 500
    assert profile.maximum_students == 1
    assert profile.session_reserve_seconds == 600
    assert profile.minimum_full_stage_per_improvement == 0.005
    assert profile.maximum_unknown_phone_record_rate == 0.05


def test_all_declared_profiles_load() -> None:
    assert {
        load_training_profile(PROFILES, name).name
        for name in ("smoke", "deadline_7day", "research_full")
    } == set(TrainingProfileName)


def test_binding_changes_when_repository_commit_changes() -> None:
    profile = load_training_profile(PROFILES, "deadline_7day")

    first = build_run_binding(profile, _immutable_inputs(repository_commit="a" * 40))
    second = build_run_binding(profile, _immutable_inputs(repository_commit="b" * 40))

    assert first["binding_sha256"] != second["binding_sha256"]
    assert first["evidence_scope"] == "adult_tamil_engineering_proxy"
    assert first["production_ready"] is False


def test_binding_requires_exact_immutable_input_fields() -> None:
    profile = load_training_profile(PROFILES, "deadline_7day")
    incomplete = _immutable_inputs()
    incomplete.pop("inventory_sha256")

    with pytest.raises(ValueError, match="immutable run-binding fields differ"):
        build_run_binding(profile, incomplete)


def test_profile_loader_rejects_duplicate_names(tmp_path: Path) -> None:
    profile = {
        "name": "smoke",
        "reference_epochs": {
            "head_only": 1,
            "top_encoder_blocks": 1,
            "full_encoder": 1,
        },
        "student_epochs": 1,
        "maximum_students": 1,
        "batch_size": 1,
        "gradient_accumulation": 1,
        "bucket_size": 16,
        "checkpoint_every_updates": 2,
        "session_max_seconds": 1800,
        "session_reserve_seconds": 120,
        "minimum_full_stage_per_improvement": 0.005,
        "maximum_unknown_phone_record_rate": 0.05,
        "split_limits": {"train": 64, "validation": 16, "test": 16},
    }
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps({"schema_version": "1.0", "profiles": [profile, profile]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate training profile"):
        load_training_profile(path, "smoke")


def test_profile_loader_rejects_reserve_that_consumes_session(tmp_path: Path) -> None:
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "profiles": [
                    {
                        "name": "smoke",
                        "reference_epochs": {
                            "head_only": 1,
                            "top_encoder_blocks": 1,
                            "full_encoder": 1,
                        },
                        "student_epochs": 1,
                        "maximum_students": 1,
                        "batch_size": 1,
                        "gradient_accumulation": 1,
                        "bucket_size": 16,
                        "checkpoint_every_updates": 2,
                        "session_max_seconds": 120,
                        "session_reserve_seconds": 120,
                        "minimum_full_stage_per_improvement": 0.005,
                        "maximum_unknown_phone_record_rate": 0.05,
                        "split_limits": {"train": 64, "validation": 16, "test": 16},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="session reserve must be shorter"):
        load_training_profile(path, "smoke")
