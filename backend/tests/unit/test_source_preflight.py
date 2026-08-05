from __future__ import annotations

import json
from pathlib import Path

import pytest
from modeling.data.source_preflight import ResearchSource, SourceCatalog, load_source_catalog
from pydantic import ValidationError

CONFIG_PATH = Path("modeling/configs/tamil_research_sources.json")


def _valid_source(**overrides: object) -> dict[str, object]:
    source: dict[str, object] = {
        "source_id": "example-source",
        "organization": "Example Org",
        "canonical_url": "https://example.org/dataset",
        "language": "ta",
        "license_spdx": "CC-BY-4.0",
        "revision": "a" * 40,
        "target_age_scope": "adult_only",
        "transcript_scope": "sentence_transcripts",
        "streaming_supported": True,
        "requires_user_terms_acceptance": False,
        "automatic_download_allowed": True,
        "dataset_license_review_required": False,
        "allowed_evidence_claims": ["engineering_proxy"],
    }
    source.update(overrides)
    return source


def test_catalog_contains_pinned_fail_closed_research_sources() -> None:
    catalog = load_source_catalog(CONFIG_PATH)

    assert catalog.catalog_version == "2026-08-05"
    assert {source.source_id for source in catalog.sources} == {
        "ai4bharat-indicvoices",
        "ai4bharat-vistaar",
        "openslr-127-iisc-mile-tamil",
    }
    assert all(len(source.revision) in {40, 64} for source in catalog.sources)
    assert all(str(source.canonical_url).startswith("https://") for source in catalog.sources)


def test_indicvoices_is_adult_only_gated_and_not_auto_downloadable() -> None:
    catalog = load_source_catalog(CONFIG_PATH)
    source = catalog.by_id("ai4bharat-indicvoices")

    assert source.target_age_scope == "adult_only"
    assert source.requires_user_terms_acceptance is True
    assert source.automatic_download_allowed is False
    assert source.allowed_evidence_claims == ("engineering_proxy",)


def test_vistaar_requires_dataset_specific_license_review() -> None:
    catalog = load_source_catalog(CONFIG_PATH)
    source = catalog.by_id("ai4bharat-vistaar")

    assert source.dataset_license_review_required is True
    assert source.automatic_download_allowed is False
    assert "dataset_discovery" in source.allowed_evidence_claims


def test_iisc_mile_is_adult_cc_by_2_and_requires_local_archive_digest() -> None:
    source = load_source_catalog(CONFIG_PATH).by_id("openslr-127-iisc-mile-tamil")

    assert source.license_spdx == "CC-BY-2.0"
    assert source.target_age_scope == "adult_only"
    assert source.automatic_download_allowed is False
    assert source.streaming_supported is False
    assert source.allowed_evidence_claims == ("engineering_proxy",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("canonical_url", "http://example.org/data"),
        ("revision", "main"),
        ("revision", "not-a-commit"),
        ("license_spdx", "unknown"),
    ],
)
def test_source_rejects_unpinned_or_unapproved_inputs(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        ResearchSource.model_validate(_valid_source(**{field: value}))


def test_terms_controlled_source_cannot_enable_automatic_download() -> None:
    with pytest.raises(ValidationError, match="terms acceptance"):
        ResearchSource.model_validate(
            _valid_source(
                requires_user_terms_acceptance=True,
                automatic_download_allowed=True,
            )
        )


def test_adult_source_cannot_claim_child_or_clinical_evidence() -> None:
    with pytest.raises(ValidationError, match="adult-only"):
        ResearchSource.model_validate(
            _valid_source(allowed_evidence_claims=["child_pronunciation_accuracy"])
        )


def test_duplicate_source_ids_are_rejected() -> None:
    duplicate = _valid_source()
    with pytest.raises(ValidationError, match="duplicate source_id"):
        SourceCatalog.model_validate(
            {"catalog_version": "test", "sources": [duplicate, duplicate]}
        )


def test_loader_rejects_unknown_fields(tmp_path: Path) -> None:
    source = _valid_source(unreviewed_extra=True)
    path = tmp_path / "sources.json"
    path.write_text(
        json.dumps({"catalog_version": "test", "sources": [source]}),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_source_catalog(path)
