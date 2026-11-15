"""Owned evaluation recordings are labelled conservatively and never promoted by filename alone."""

from pathlib import Path
import subprocess
import sys

from app.vaakmitra_word.owned_recordings import classify_recording_name


def test_child_word_sequence_remains_validation_only() -> None:
    label = classify_recording_name("1Words.wav")

    assert label.speaker_role == "child"
    assert label.speaker_pseudonym == "owned-child-001"
    assert label.content_kind == "word_sequence"
    assert label.permitted_use == "child_validation_only"
    assert label.reference_eligible is False


def test_therapist_vocalization_is_not_mislabeled_as_target_word() -> None:
    label = classify_recording_name("Sir_aa.wav")

    assert label.speaker_role == "adult_therapist"
    assert label.speaker_pseudonym == "owned-therapist-001"
    assert label.content_kind == "vocalization"
    assert label.permitted_use == "adult_engineering_evaluation"
    assert label.canonical_word_id is None
    assert label.reference_eligible is False


def test_environmental_audio_is_negative_canary_candidate() -> None:
    label = classify_recording_name("Room_noise.wav")

    assert label.speaker_role == "environment"
    assert label.content_kind == "environmental_noise"
    assert label.permitted_use == "negative_canary_candidate"
    assert label.reference_eligible is False


def test_unknown_filename_fails_to_review_required() -> None:
    label = classify_recording_name("mystery.wav")

    assert label.speaker_role == "unknown"
    assert label.content_kind == "unknown"
    assert label.permitted_use == "review_required"
    assert label.reference_eligible is False


def test_owned_recording_inventory_cli_is_directly_runnable() -> None:
    backend_root = Path(__file__).resolve().parents[2]

    completed = subprocess.run(
        [sys.executable, "scripts/model/transcribe_owned_recordings.py", "--help"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--input-root" in completed.stdout
    assert "--model-sha256" in completed.stdout
