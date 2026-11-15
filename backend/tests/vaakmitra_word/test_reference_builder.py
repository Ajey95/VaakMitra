"""Balanced bank selection for DEC-017, DTW-005/007, and DATA-010/012."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from app.vaakmitra_word.dtw import ReferenceEmbedding
from app.vaakmitra_word.reference_builder import (
    ReferenceCandidate,
    ReferenceBankBuildError,
    load_reference_bank_artifact,
    save_reference_bank_artifact,
    select_balanced_references,
)


def test_selection_requires_32_references_from_at_least_eight_speakers() -> None:
    """A large pile from too few speakers must leave the word inactive."""
    candidates = [_candidate(index, speaker=f"speaker-{index % 7}") for index in range(70)]

    result = select_balanced_references(candidates)

    assert result.active is False
    assert result.selected == ()
    assert "insufficient_speakers" in result.reasons


def test_selection_caps_each_speaker_at_four_and_total_at_64() -> None:
    """Neither a prolific speaker nor unlimited bank growth may dominate matching."""
    candidates = [
        _candidate(speaker_index * 20 + clip, speaker=f"speaker-{speaker_index}")
        for speaker_index in range(20)
        for clip in range(20)
    ]

    result = select_balanced_references(candidates)
    speaker_counts = Counter(item.speaker_pseudonym for item in result.selected)

    assert result.active is True
    assert len(result.selected) == 64
    assert len(speaker_counts) == 20
    assert max(speaker_counts.values()) <= 4


def test_selection_is_deterministic_and_excludes_unapproved_or_invalid_embeddings() -> None:
    """Reordering input or adding rejected records must not change the release bank."""
    candidates = [
        _candidate(speaker_index * 4 + clip, speaker=f"speaker-{speaker_index}")
        for speaker_index in range(8)
        for clip in range(4)
    ]
    candidates.extend(
        (
            _candidate(1000, speaker="speaker-extra", approved=False),
            _candidate(1001, speaker="speaker-extra", finite=False),
        )
    )

    first = select_balanced_references(candidates)
    second = select_balanced_references(list(reversed(candidates)))

    assert first.active is True
    assert len(first.selected) == 32
    assert [item.sample_id for item in first.selected] == [
        item.sample_id for item in second.selected
    ]
    assert all(item.approved for item in first.selected)
    assert all(np.isfinite(item.embedding).all() for item in first.selected)


def test_reference_artifact_round_trip_preserves_speaker_identity(tmp_path: Path) -> None:
    candidates = [
        _candidate(speaker_index * 4 + clip, speaker=f"speaker-{speaker_index}")
        for speaker_index in range(8)
        for clip in range(4)
    ]
    selection = select_balanced_references(candidates)
    path = tmp_path / "reference-bank.npz"

    save_reference_bank_artifact(
        path,
        selections={"TA_WORD_0001": selection},
        version="adult-reference-v1",
        model_hash="a" * 64,
        vocabulary_hash="b" * 64,
        dataset_manifest_hash="c" * 64,
    )
    bank = load_reference_bank_artifact(
        path,
        expected_model_hash="a" * 64,
        expected_vocabulary_hash="b" * 64,
    )

    references = bank.references["TA_WORD_0001"]
    assert len(references) == 32
    assert all(isinstance(reference, ReferenceEmbedding) for reference in references)
    assert len({reference.speaker_pseudonym for reference in references}) == 8


def test_reference_artifact_refuses_inactive_or_empty_selection(tmp_path: Path) -> None:
    inactive = select_balanced_references(
        [_candidate(index, speaker=f"speaker-{index % 7}") for index in range(32)]
    )

    with pytest.raises(ReferenceBankBuildError, match="no_active_words"):
        save_reference_bank_artifact(
            tmp_path / "reference-bank.npz",
            selections={"TA_WORD_0001": inactive},
            version="adult-reference-v1",
            model_hash="a" * 64,
            vocabulary_hash="b" * 64,
            dataset_manifest_hash="c" * 64,
        )


def test_reference_builder_cli_runs_directly_from_backend_root() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "scripts/model/build_reference_bank.py", "--help"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--approval-manifest" in completed.stdout


def _candidate(
    index: int,
    *,
    speaker: str,
    approved: bool = True,
    finite: bool = True,
) -> ReferenceCandidate:
    value = float(index + 1) if finite else np.nan
    return ReferenceCandidate(
        sample_id=f"sample-{index:04d}",
        word_id="TA_WORD_0001",
        speaker_pseudonym=speaker,
        source_id="source-a",
        quality_score=1.0 - (index % 10) / 100.0,
        approved=approved,
        embedding=np.full((2, 3), value, dtype=np.float32),
    )
