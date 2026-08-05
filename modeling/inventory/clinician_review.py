"""Fail-closed Tamil expert review contract for a candidate phoneme inventory."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from modeling.inventory.consensus import AllophoneRule, CandidateInventory

ReviewDecision = Literal["pending", "approve", "reject", "replace", "needs_discussion"]


def _token(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.strip())
    if not normalized:
        raise ValueError("phone tokens must be non-empty")
    if normalized == "<blank>":
        raise ValueError("the blank token cannot be reviewed or used as a replacement")
    return normalized


class TokenReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str
    decision: ReviewDecision = "pending"
    replacement_token: str | None = None
    notes: str = ""

    @field_validator("token")
    @classmethod
    def normalize_token(cls, value: str) -> str:
        return _token(value)

    @field_validator("replacement_token")
    @classmethod
    def normalize_replacement(cls, value: str | None) -> str | None:
        return None if value is None else _token(value)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_replacement(self) -> Self:
        if self.decision == "replace" and self.replacement_token is None:
            raise ValueError("replace decisions require a replacement token")
        if self.decision != "replace" and self.replacement_token is not None:
            raise ValueError("replacement token is allowed only for replace decisions")
        return self


class AllophoneReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    canonical: str
    decision: Literal["pending", "approve", "reject", "needs_discussion"] = "pending"
    notes: str = ""

    @field_validator("source", "canonical")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return _token(value)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str) -> str:
        return value.strip()


class ReviewPolicies(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    vowel_length: Literal[
        "pending", "needs_discussion", "contrastive_separate_length_mark", "merge_length"
    ] = "pending"
    gemination: Literal[
        "pending",
        "needs_discussion",
        "contrastive_repeated_consonant",
        "single_phone_with_duration_feature",
    ] = "pending"
    allophones: Literal[
        "pending", "needs_discussion", "explicit_reviewed_mappings_only"
    ] = "pending"
    unknown_phone: Literal[
        "pending", "needs_discussion", "unscorable_fail_closed", "research_unk_only"
    ] = "pending"


class ReviewerAttestation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["tamil_linguist", "speech_language_pathologist", "speech_scientist"]
    organization: str = Field(min_length=2)
    reviewed_at: datetime
    attests_inventory_reviewed: bool

    @field_validator("organization")
    @classmethod
    def normalize_organization(cls, value: str) -> str:
        return value.strip()

    @field_validator("reviewed_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("reviewed_at must be expressed in UTC")
        return value.astimezone(timezone.utc)


class ClinicianReviewPacket(BaseModel):
    """Editable review record bound to one immutable candidate inventory digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    review_status: Literal["pending_expert_review"] = "pending_expert_review"
    candidate_inventory_version: str = Field(min_length=1)
    candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    token_reviews: tuple[TokenReview, ...] = Field(min_length=1)
    allophone_reviews: tuple[AllophoneReview, ...]
    policies: ReviewPolicies
    reviewer: ReviewerAttestation | None = None

    def digest(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


class ApprovedInventory(BaseModel):
    """Expert-reviewed vocabulary; clinical/model/device gates remain separate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    review_status: Literal["expert_approved"] = "expert_approved"
    inventory_version: str
    source_candidate_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    blank_token: Literal["<blank>"] = "<blank>"
    tokens: tuple[str, ...] = Field(min_length=2)
    allophones: tuple[AllophoneRule, ...]
    vowel_length_policy: Literal[
        "contrastive_separate_length_mark", "merge_length"
    ]
    gemination_policy: Literal[
        "contrastive_repeated_consonant", "single_phone_with_duration_feature"
    ]
    allophone_policy: Literal["explicit_reviewed_mappings_only"]
    unknown_phone_policy: Literal["unscorable_fail_closed", "research_unk_only"]
    reviewer: ReviewerAttestation
    expert_approved: Literal[True] = True
    production_ready: Literal[False] = False
    evidence_scope: Literal["expert_reviewed_inventory_not_clinically_validated"] = (
        "expert_reviewed_inventory_not_clinically_validated"
    )

    @model_validator(mode="after")
    def validate_vocabulary(self) -> Self:
        if self.tokens[0] != self.blank_token:
            raise ValueError("blank token must remain at index zero")
        if len(self.tokens) != len(set(self.tokens)):
            raise ValueError("approved phone tokens must be unique")
        known = set(self.tokens[1:])
        if any(rule.canonical not in known for rule in self.allophones):
            raise ValueError("approved allophone target must exist in the vocabulary")
        return self


def create_review_template(candidate: CandidateInventory) -> ClinicianReviewPacket:
    """Create a pending review form containing every token and allophone rule."""

    return ClinicianReviewPacket(
        candidate_inventory_version=candidate.inventory_version,
        candidate_digest=candidate.digest(),
        token_reviews=tuple(TokenReview(token=token) for token in candidate.tokens[1:]),
        allophone_reviews=tuple(
            AllophoneReview(source=rule.source, canonical=rule.canonical)
            for rule in candidate.allophones
        ),
        policies=ReviewPolicies(),
    )


def _require_complete_review(packet: ClinicianReviewPacket) -> ReviewerAttestation:
    if packet.reviewer is None:
        raise ValueError("reviewer attestation is required")
    if not packet.reviewer.attests_inventory_reviewed:
        raise ValueError("reviewer attestation must be true")
    if any(
        item.decision in {"pending", "needs_discussion"} or not item.notes
        for item in packet.token_reviews
    ):
        raise ValueError("token review contains a pending decision or missing notes")
    if any(
        item.decision in {"pending", "needs_discussion"} or not item.notes
        for item in packet.allophone_reviews
    ):
        raise ValueError("allophone review contains a pending decision or missing notes")
    policy_values = tuple(packet.policies.model_dump().values())
    if any(value in {"pending", "needs_discussion"} for value in policy_values):
        raise ValueError("every inventory policy requires a final expert decision")
    return packet.reviewer


def finalize_expert_inventory(
    candidate: CandidateInventory, packet: ClinicianReviewPacket
) -> ApprovedInventory:
    """Apply a complete attested review; fail on omissions, tampering, or ambiguity."""

    if packet.candidate_digest != candidate.digest():
        raise ValueError("review packet candidate digest does not match")
    if packet.candidate_inventory_version != candidate.inventory_version:
        raise ValueError("review packet candidate version does not match")
    expected_tokens = set(candidate.tokens[1:])
    reviewed_tokens = [item.token for item in packet.token_reviews]
    if len(reviewed_tokens) != len(set(reviewed_tokens)) or set(reviewed_tokens) != expected_tokens:
        raise ValueError("token reviews must exactly cover the candidate vocabulary")
    expected_allophones = {(rule.source, rule.canonical) for rule in candidate.allophones}
    reviewed_allophones = [
        (item.source, item.canonical) for item in packet.allophone_reviews
    ]
    if (
        len(reviewed_allophones) != len(set(reviewed_allophones))
        or set(reviewed_allophones) != expected_allophones
    ):
        raise ValueError("allophone reviews must exactly cover candidate mappings")
    reviewer = _require_complete_review(packet)

    approved_tokens = {
        item.replacement_token if item.decision == "replace" else item.token
        for item in packet.token_reviews
        if item.decision in {"approve", "replace"}
    }
    if None in approved_tokens:
        raise ValueError("replace decision is missing its replacement token")
    token_strings = {str(token) for token in approved_tokens}
    approved_allophones = tuple(
        AllophoneRule(
            source=item.source,
            canonical=item.canonical,
            provenance=f"expert_review:{packet.digest()}",
        )
        for item in packet.allophone_reviews
        if item.decision == "approve"
    )
    policies = packet.policies.model_dump()
    return ApprovedInventory.model_validate(
        {
            "inventory_version": f"{candidate.inventory_version}-expert-reviewed",
            "source_candidate_digest": candidate.digest(),
            "review_digest": packet.digest(),
            "tokens": ("<blank>", *sorted(token_strings)),
            "allophones": approved_allophones,
            "vowel_length_policy": policies["vowel_length"],
            "gemination_policy": policies["gemination"],
            "allophone_policy": policies["allophones"],
            "unknown_phone_policy": policies["unknown_phone"],
            "reviewer": reviewer,
        }
    )
