"""DEC-049 / PHN-001,006: validate imported encoder before file reconstruction."""

import hashlib
import json
from pathlib import Path

import app.vaakmitra_word.mobile_student_model as encoder


def validate_ensemble_dependencies(checkpoint, state):
    """Legacy singles are unchanged; unwitnessed old ensembles fail closed."""
    if state.get("model_kind", "single") != "posterior_mean_2":
        return
    checkpoint = Path(checkpoint)
    expected = state.get("encoder_architecture_source_sha256")
    witness_path = checkpoint.parent / "pre-evaluation-freeze.json"
    if witness_path.exists():
        witness = json.loads(witness_path.read_text(encoding="utf8"))
        if (
            witness.get("checkpoint_sha256")
            != hashlib.sha256(checkpoint.read_bytes()).hexdigest()
            or witness.get("architecture_source_sha256")
            != state.get("architecture_source_sha256")
            or (
                expected is not None
                and expected != witness.get("encoder_architecture_source_sha256")
            )
        ):
            raise ValueError("ensemble encoder dependency witness differs")
        expected = witness.get("encoder_architecture_source_sha256")
    if (
        not expected
        or hashlib.sha256(Path(encoder.__file__).read_bytes()).hexdigest() != expected
    ):
        raise ValueError("ensemble encoder dependency missing or changed")
