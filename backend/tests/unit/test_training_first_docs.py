from pathlib import Path


def test_runbook_contains_deadline_launch_and_recovery_commands() -> None:
    text = Path("modeling/training/gpu/README.md").read_text(encoding="utf-8")

    assert 'TRAINING_PROFILE_NAME="deadline_7day"' in text
    assert "canary-report.json" in text
    assert "checkpoint every 500 optimizer updates" in text
    assert "rerun from the configuration cell" in text
    assert "adult Tamil engineering proxy" in text
    assert "not child or clinical validation" in text
    assert "/content/drive/MyDrive/VaakMitraGPU/inputs/" in text
    assert "HF_TOKEN" in text


def test_preflight_has_measured_gates_and_native_checkpoint_handoff() -> None:
    text = Path("docs/verification/training-first-colab-preflight.md").read_text(
        encoding="utf-8"
    )

    for required in (
        "1,800 seconds",
        "Mid-epoch resume",
        "Non-finite loss",
        "production ready false",
        "selected native checkpoint",
        "exact 40-character Git commit",
    ):
        assert required in text


def test_top_level_readme_points_to_training_first_handoff() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "Training-first Colab handoff" in text
    assert "docs/verification/training-first-colab-preflight.md" in text
