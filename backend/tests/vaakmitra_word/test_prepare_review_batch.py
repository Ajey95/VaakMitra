"""GOV-003..005: candidate packets contain hashes/IDs, never recordings."""

import json
from pathlib import Path

from app.vaakmitra_word.corpus import CorpusRecord
from app.vaakmitra_word.model import sha256_file
from scripts.model.prepare_review_batch import reference_batch_from_manifest


def test_gov003_reference_packet_has_exact_source_hash_and_metadata_only(tmp_path: Path):
    manifest = tmp_path / "source.jsonl"
    record = CorpusRecord(
        schema_version="vaakmitra-corpus-record-1", sample_id="s1",
        source_id="public", source_revision="v1", original_id="clip-1",
        speaker_pseudonym="speaker-1", canonical_word_id="TA_WORD_0001",
        label_kind="target", audio_path="private-source/clip.wav",
        audio_sha256="a" * 64, duration_seconds=0.7, split="reference",
        licence_id="verified",
    )
    manifest.write_text(record.model_dump_json() + "\n", encoding="utf-8")

    packet = reference_batch_from_manifest(manifest)

    assert packet["kind"] == "reference"
    assert packet["manifest_sha256"] == sha256_file(manifest)
    assert packet["items"] == [{
        "item_id": "s1", "word_id": "TA_WORD_0001", "audio_sha256": "a" * 64,
        "source_sample_id": None, "category": None, "expected_decision": None,
        "content_sha256": None,
    }]
    assert "private-source/clip.wav" not in json.dumps(packet)
