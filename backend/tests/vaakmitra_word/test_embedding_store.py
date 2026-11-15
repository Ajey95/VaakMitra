"""Governed encoder embedding shards (MOD-001..008, DATA-008)."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from app.vaakmitra_word.embedding_store import (
    EmbeddingItem,
    EmbeddingShardError,
    completed_sample_ids,
    load_embedding_shard,
    write_embedding_shard,
)


HASHES = {
    "model_hash": "a" * 64,
    "vocabulary_hash": "b" * 64,
    "source_manifest_hash": "c" * 64,
}


def test_shard_round_trip_preserves_metadata_and_frame_arrays(tmp_path: Path) -> None:
    path = tmp_path / "shard-00001.npz"
    items = [
        EmbeddingItem("sample-a", "TA_WORD_0001", "speaker-a", "train", np.ones((5, 3))),
        EmbeddingItem("sample-b", None, "speaker-b", "evaluation", np.full((7, 3), 2.0)),
    ]

    written = write_embedding_shard(path, shard_id="shard-00001", items=items, **HASHES)
    loaded = load_embedding_shard(path, **HASHES)

    assert written == loaded.manifest_sha256
    assert loaded.manifest.schema_version == "vaakmitra-embedding-shard-1"
    assert [item.sample_id for item in loaded.items] == ["sample-a", "sample-b"]
    assert loaded.items[0].embedding.shape == (5, 3)
    assert loaded.items[1].canonical_word_id is None


@pytest.mark.parametrize(
    "embedding",
    [np.ones(3), np.empty((0, 3)), np.array([[np.nan, 1.0]])],
)
def test_invalid_embeddings_are_rejected_before_writing(
    tmp_path: Path,
    embedding: np.ndarray,
) -> None:
    item = EmbeddingItem("sample-a", "TA_WORD_0001", "speaker-a", "train", embedding)

    with pytest.raises(EmbeddingShardError, match="embedding_invalid"):
        write_embedding_shard(
            tmp_path / "bad.npz",
            shard_id="bad",
            items=[item],
            **HASHES,
        )


def test_expected_hash_mismatch_rejects_shard(tmp_path: Path) -> None:
    path = tmp_path / "shard.npz"
    write_embedding_shard(
        path,
        shard_id="shard",
        items=[EmbeddingItem("sample-a", None, "speaker-a", "train", np.ones((2, 2)))],
        **HASHES,
    )

    with pytest.raises(EmbeddingShardError, match="model_hash_mismatch"):
        load_embedding_shard(path, **{**HASHES, "model_hash": "d" * 64})


def test_corrupt_shard_is_rejected_instead_of_counted_as_resumable(tmp_path: Path) -> None:
    (tmp_path / "shard-00001.npz").write_bytes(b"not-an-npz")

    with pytest.raises(EmbeddingShardError, match="shard_payload_invalid"):
        completed_sample_ids(tmp_path, **HASHES)


def test_completed_ids_support_resuming_without_duplicate_inference(tmp_path: Path) -> None:
    write_embedding_shard(
        tmp_path / "shard-00001.npz",
        shard_id="shard-00001",
        items=[EmbeddingItem("sample-a", None, "speaker-a", "train", np.ones((2, 2)))],
        **HASHES,
    )
    write_embedding_shard(
        tmp_path / "shard-00002.npz",
        shard_id="shard-00002",
        items=[EmbeddingItem("sample-b", "TA_WORD_0002", "speaker-b", "train", np.ones((3, 2)))],
        **HASHES,
    )

    assert completed_sample_ids(tmp_path, **HASHES) == {"sample-a", "sample-b"}


def test_existing_shard_is_never_silently_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "shard.npz"
    path.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        write_embedding_shard(
            path,
            shard_id="shard",
            items=[EmbeddingItem("sample-a", None, "speaker-a", "train", np.ones((2, 2)))],
            **HASHES,
        )


def test_embedding_extraction_cli_runs_directly_from_backend_root() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "scripts/model/extract_embeddings.py", "--help"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--source-manifest" in completed.stdout
