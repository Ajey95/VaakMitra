"""OpenSLR 65 sentences stay non-target until reviewed word segmentation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile

from app.vaakmitra_word.corpus import SourceEntry, validate_jsonl_manifest
from app.vaakmitra_word.openslr65 import OpenSlr65Partition, build_openslr65_manifest


def test_sentence_manifest_is_other_only_and_speaker_disjoint(tmp_path: Path) -> None:
    root = tmp_path / "audio"
    root.mkdir()
    samples = (np.sin(np.linspace(0, 100, 16_000)) * 10_000).astype("<i2")
    for file_id in (
        "taf_00001_00000000001",
        "taf_00001_00000000002",
        "taf_00001_00000000003",
    ):
        wavfile.write(root / f"{file_id}.wav", 16_000, samples)
    index = root / "line_index.tsv"
    index.write_text(
        "taf_00001_00000000001\tஅம்மா வீட்டில் உள்ளார்\n"
        "taf_00001_00000000002\tவேறு வாக்கியம்\n"
        "taf_00001_00000000003\t\n",
        encoding="utf-8",
    )
    output = tmp_path / "manifest.jsonl"

    count = build_openslr65_manifest(
        (OpenSlr65Partition(index_path=index, audio_root=root),),
        corpus_root=root,
        output_path=output,
        source=_source(),
        seed=31,
    )
    summary = validate_jsonl_manifest(output)

    assert count == 3
    assert summary.other_records == 3
    assert summary.target_records == 0
    assert summary.speakers == 1
    assert '"canonical_word_id":null' in output.read_text(encoding="utf-8")
    assert '"transcript":null' in output.read_text(encoding="utf-8")


def _source() -> SourceEntry:
    return SourceEntry(
        source_id="openslr-65-ta",
        source_revision="openslr65-2019-metadata-533be052-1a0c01af",
        homepage="https://openslr.org/65/",
        licence_id="CC-BY-SA-4.0",
        licence_url="https://creativecommons.org/licenses/by-sa/4.0/",
        licence_status="verified",
        terms_checked_at="2026-09-06",
        enabled=True,
        intended_uses=("target", "other", "confusable", "canary"),
    )
