"""MLCommons Tamil data enters only as governed OTHER/confusable evidence."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from app.vaakmitra_word.corpus import SourceEntry, validate_jsonl_manifest
from app.vaakmitra_word.mswc import build_mswc_manifest


def test_mswc_manifest_is_other_only_and_speaker_disjoint(tmp_path: Path) -> None:
    audio_root = tmp_path / "audio"
    audio_root.mkdir()
    samples = (np.sin(np.linspace(0, 100, 16_000)) * 10_000).astype("<i2")
    for name in ("சொல்_one.wav", "வேறு_two.wav"):
        wavfile.write(audio_root / name, 16_000, samples)
    csv_path = tmp_path / "split.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as sink:
        writer = csv.DictWriter(sink, fieldnames=("LINK", "WORD", "VALID", "SPEAKER", "GENDER"))
        writer.writeheader()
        writer.writerow({"LINK": "சொல்/one.wav", "WORD": "சொல்", "VALID": "True", "SPEAKER": "same", "GENDER": "MALE"})
        writer.writerow({"LINK": "வேறு/two.wav", "WORD": "வேறு", "VALID": "True", "SPEAKER": "same", "GENDER": "MALE"})
    output = tmp_path / "manifest.jsonl"

    count = build_mswc_manifest(
        (csv_path,),
        audio_root=audio_root,
        output_path=output,
        source=_source(),
        seed=29,
    )
    summary = validate_jsonl_manifest(output, audio_root=audio_root)

    assert count == 2
    assert summary.other_records == 2
    assert summary.target_records == 0
    assert summary.speakers == 1
    lines = output.read_text(encoding="utf-8").splitlines()
    assert all('"canonical_word_id":null' in line for line in lines)


def _source() -> SourceEntry:
    return SourceEntry(
        source_id="mlcommons-mswc-ta",
        source_revision="0bc9df68e92fd6bb54176bf7eb29e2b9e97cb218",
        homepage="https://example.invalid",
        licence_id="CC-BY-4.0",
        licence_url="https://example.invalid/license",
        licence_status="verified",
        terms_checked_at="2026-09-06",
        enabled=True,
        intended_uses=("other", "confusable"),
    )
