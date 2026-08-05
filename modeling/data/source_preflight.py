"""Fail-closed metadata validation for research-only Tamil speech sources."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

_IMMUTABLE_REVISION = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_DISALLOWED_ADULT_CLAIM_TERMS = ("child", "clinical", "therapy", "diagnosis")


class ResearchSource(BaseModel):
    """Audited source metadata; this model does not download any data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    APPROVED_LICENSES: ClassVar[frozenset[str]] = frozenset(
        {"Apache-2.0", "CC-BY-4.0", "CC0-1.0", "MIT"}
    )

    source_id: str = Field(min_length=1)
    organization: str = Field(min_length=1)
    canonical_url: HttpUrl
    language: Literal["ta"]
    license_spdx: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    target_age_scope: Literal["adult_only", "mixed_or_unknown", "child_approved"]
    transcript_scope: str = Field(min_length=1)
    streaming_supported: bool
    requires_user_terms_acceptance: bool
    automatic_download_allowed: bool
    dataset_license_review_required: bool
    allowed_evidence_claims: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_safety_contract(self) -> ResearchSource:
        if self.canonical_url.scheme != "https":
            raise ValueError("canonical_url must use HTTPS")
        if not _IMMUTABLE_REVISION.fullmatch(self.revision):
            raise ValueError("revision must be an immutable 40- or 64-character commit hash")
        if self.license_spdx not in self.APPROVED_LICENSES:
            raise ValueError("license_spdx is not in the approved allowlist")
        if self.requires_user_terms_acceptance and self.automatic_download_allowed:
            raise ValueError("a source requiring terms acceptance cannot allow automatic download")
        if self.dataset_license_review_required and self.automatic_download_allowed:
            raise ValueError("license review must finish before automatic download")
        if self.target_age_scope == "adult_only":
            unsafe_claims = [
                claim
                for claim in self.allowed_evidence_claims
                if any(term in claim.casefold() for term in _DISALLOWED_ADULT_CLAIM_TERMS)
            ]
            if unsafe_claims:
                raise ValueError("adult-only data cannot support child, clinical, or therapy claims")
        return self


class SourceCatalog(BaseModel):
    """Versioned, unique set of research source preflight records."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    catalog_version: str = Field(min_length=1)
    sources: tuple[ResearchSource, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_source_ids(self) -> SourceCatalog:
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("duplicate source_id values are not allowed")
        return self

    def by_id(self, source_id: str) -> ResearchSource:
        """Return a source by stable identifier."""

        for source in self.sources:
            if source.source_id == source_id:
                return source
        raise KeyError(source_id)


def load_source_catalog(path: Path) -> SourceCatalog:
    """Read and validate a UTF-8 research source catalog."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return SourceCatalog.model_validate(payload)
