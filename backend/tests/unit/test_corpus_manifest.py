from __future__ import annotations

import json

import pytest
from modeling.data.corpus_manifest import CorpusManifest
from pydantic import ValidationError

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64


def _valid_proxy_manifest() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "dataset_id": "fixture/tamil-phoneme-proxy",
        "revision": "1d6a78e02c6c21d8da30eb57dd4dc02b4ed765f5",
        "source_url": "https://huggingface.co/datasets/fixture/tamil-phoneme-proxy",
        "license_spdx": "CC0-1.0",
        "population": "adult_tamil_proxy",
        "label_origin": "dataset_supplied_phonemes",
        "evidence_scope": "engineering_proxy",
        "local_processing_only": True,
        "splits": [
            {
                "name": "train",
                "speakers": ["adult-a", "adult-b"],
                "record_count": 100,
                "index_sha256": _SHA_A,
            },
            {
                "name": "validation",
                "speakers": ["adult-c"],
                "record_count": 20,
                "index_sha256": _SHA_B,
            },
            {
                "name": "test",
                "speakers": ["adult-d"],
                "record_count": 20,
                "index_sha256": _SHA_C,
            },
        ],
    }


def test_proxy_manifest_rejects_missing_or_unapproved_licence() -> None:
    for licence in ("", "NOASSERTION", "CC-BY-NC-ND-4.0"):
        payload = _valid_proxy_manifest()
        payload["license_spdx"] = licence

        with pytest.raises(ValidationError, match="approved SPDX licence"):
            CorpusManifest.model_validate(payload)


def test_proxy_manifest_rejects_mutable_revision() -> None:
    payload = _valid_proxy_manifest()
    payload["revision"] = "main"

    with pytest.raises(ValidationError, match="immutable revision"):
        CorpusManifest.model_validate(payload)


def test_proxy_manifest_requires_local_only_processing() -> None:
    payload = _valid_proxy_manifest()
    payload["local_processing_only"] = False

    with pytest.raises(ValidationError, match="local_processing_only"):
        CorpusManifest.model_validate(payload)


def test_proxy_manifest_rejects_target_user_claim_for_adult_data() -> None:
    payload = _valid_proxy_manifest()
    payload["evidence_scope"] = "target_user_validation"

    with pytest.raises(ValidationError, match="target-user evidence"):
        CorpusManifest.model_validate(payload)


def test_target_user_manifest_requires_therapist_adjudicated_labels() -> None:
    payload = _valid_proxy_manifest()
    payload["population"] = "target_user_child"
    payload["evidence_scope"] = "target_user_validation"

    with pytest.raises(ValidationError, match="therapist_adjudicated"):
        CorpusManifest.model_validate(payload)


def test_proxy_manifest_rejects_speaker_overlap() -> None:
    payload = _valid_proxy_manifest()
    splits = payload["splits"]
    assert isinstance(splits, list)
    splits[1]["speakers"] = ["adult-a"]

    with pytest.raises(ValidationError, match="speaker-disjoint"):
        CorpusManifest.model_validate(payload)


def test_proxy_manifest_requires_train_validation_and_test_splits() -> None:
    payload = _valid_proxy_manifest()
    splits = payload["splits"]
    assert isinstance(splits, list)
    splits.pop()

    with pytest.raises(ValidationError, match="train, validation, and test"):
        CorpusManifest.model_validate(payload)


def test_proxy_manifest_has_stable_canonical_digest() -> None:
    original = _valid_proxy_manifest()
    reordered = dict(reversed(original.items()))

    assert CorpusManifest.model_validate(original).digest() == CorpusManifest.model_validate(
        reordered
    ).digest()


def test_proxy_manifest_loads_from_json(tmp_path) -> None:
    manifest_path = tmp_path / "corpus.json"
    manifest_path.write_text(json.dumps(_valid_proxy_manifest()), encoding="utf-8")

    manifest = CorpusManifest.from_json(manifest_path)

    assert manifest.dataset_id == "fixture/tamil-phoneme-proxy"
    assert manifest.total_records == 140

