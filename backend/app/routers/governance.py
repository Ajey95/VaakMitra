"""GOV-001..006: authenticated metadata receipts, never delegated human approval."""

from __future__ import annotations

from datetime import datetime, timezone
import os
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pymongo.errors import DuplicateKeyError

from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import audit, oid, serialize
from ..vaakmitra_word.review_exports import clinical_bundle_hash, sign_review_export

router = APIRouter(prefix="/api/governance", tags=["governance"])

Scope = Literal["reference", "canary", "clinical"]
HASH_PATTERN = r"^[a-f0-9]{64}$"
CLINICAL_SECTIONS = frozenset({
    "vocabulary", "tamil_prompts", "voice_assets", "avatar_states",
    "result_wording", "action_set", "difficulty", "retry_break_limits",
    "test_protocol", "limitations",
})


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Mongo's default UTC datetime decoder returns naive Python values."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class CredentialInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    therapist_id: str = Field(min_length=1)
    scope: Scope
    evidence_sha256: str = Field(pattern=HASH_PATTERN)
    external_ref: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:/-]+$")


class ConsentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    purpose: Literal["child_validation", "research_retention"]
    guardian_document_sha256: str = Field(pattern=HASH_PATTERN)
    ethics_approval_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:/-]+$")
    ethics_document_sha256: str = Field(pattern=HASH_PATTERN)
    valid_from: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def valid_interval(self) -> "ConsentInput":
        if self.valid_from.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("consent timestamps must include a timezone")
        if self.expires_at <= self.valid_from:
            raise ValueError("consent expires_at must follow valid_from")
        return self


class ConsentVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    guardian_relationship_verified: bool
    ethics_approval_verified: bool


class ConsentRejection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: Literal[
        "guardian_relationship_unverified", "ethics_not_verified",
        "document_mismatch", "outside_protocol",
    ]


async def is_qualified(db, therapist_id: str, scope: Scope) -> bool:
    """GOV-002: latest independent credential event decides a reviewer's scope."""
    event = await db.reviewer_credentials.find_one(
        {"therapist_id": therapist_id, "scope": scope}, sort=[("_id", -1)]
    )
    return bool(
        event and event.get("status") == "verified"
        and event.get("verified_by") != therapist_id
        and event.get("evidence_sha256")
    )


@router.post("/credentials")
async def verify_credential(payload: CredentialInput, current_admin: dict = Depends(require_admin)):
    """GOV-002: admin records an external qualification check for another actor."""
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin_required")
    therapist_id = str(oid(payload.therapist_id))
    if therapist_id == str(current_admin["_id"]):
        raise HTTPException(status_code=403, detail="self_verification_forbidden")
    db = get_database()
    therapist = await db.users.find_one({"_id": oid(therapist_id)})
    if not therapist or therapist.get("role") != "therapist":
        raise HTTPException(status_code=404, detail="therapist_not_found")
    doc = {
        "therapist_id": therapist_id, "scope": payload.scope,
        "evidence_sha256": payload.evidence_sha256,
        "external_ref": payload.external_ref,
        "status": "verified", "verified_by": str(current_admin["_id"]),
        "created_at": utc_now(),
    }
    result = await db.reviewer_credentials.insert_one(doc)
    await audit("governance.credential_verified", current_admin, target=therapist_id,
                meta={"scope": payload.scope, "event_id": str(result.inserted_id)})
    return serialize(dict(doc, _id=result.inserted_id))


@router.post("/credentials/{therapist_id}/{scope}/revoke")
async def revoke_credential(therapist_id: str, scope: Scope, current_admin: dict = Depends(require_admin)):
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin_required")
    therapist_id = str(oid(therapist_id))
    db = get_database()
    if not await is_qualified(db, therapist_id, scope):
        raise HTTPException(status_code=404, detail="active_credential_not_found")
    doc = {
        "therapist_id": therapist_id, "scope": scope, "status": "revoked",
        "verified_by": str(current_admin["_id"]), "created_at": utc_now(),
    }
    result = await db.reviewer_credentials.insert_one(doc)
    await audit("governance.credential_revoked", current_admin, target=therapist_id,
                meta={"scope": scope, "event_id": str(result.inserted_id)})
    return serialize(dict(doc, _id=result.inserted_id))


@router.post("/consents")
async def submit_consent(payload: ConsentInput, current_user: dict = Depends(get_current_user)):
    """GOV-001: a caregiver receipt is pending, not a consent verification."""
    if current_user.get("role") != "user":
        raise HTTPException(status_code=403, detail="caregiver_account_required")
    if payload.expires_at <= utc_now():
        raise HTTPException(status_code=400, detail="consent_expired")
    db = get_database()
    doc = {
        "child_id": str(current_user["_id"]), "protocol_id": payload.protocol_id,
        "purpose": payload.purpose,
        "guardian_document_sha256": payload.guardian_document_sha256,
        "ethics_approval_id": payload.ethics_approval_id,
        "ethics_document_sha256": payload.ethics_document_sha256,
        "valid_from": payload.valid_from, "expires_at": payload.expires_at,
        "submitted_by": str(current_user["_id"]), "created_at": utc_now(),
    }
    result = await db.consent_receipts.insert_one(doc)
    await audit("governance.consent_submitted", current_user, target=str(result.inserted_id))
    return {"id": str(result.inserted_id), "status": "pending_verification",
            "effective_for_new_recordings_at": None}


@router.get("/consents/me")
async def my_consents(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "user":
        raise HTTPException(status_code=403, detail="caregiver_account_required")
    db = get_database()
    receipts = await db.consent_receipts.find({"child_id": str(current_user["_id"])}).to_list(length=100)
    output = []
    for receipt in receipts:
        receipt_id = str(receipt["_id"])
        decision = await db.consent_decisions.find_one({"receipt_id": receipt_id})
        withdrawal = await db.consent_withdrawals.find_one({"receipt_id": receipt_id})
        output.append({"id": receipt_id, "protocol_id": receipt["protocol_id"],
                       "purpose": receipt["purpose"],
                       "status": "withdrawn" if withdrawal else decision["status"] if decision else "pending_verification",
                       "effective_for_new_recordings_at": None if withdrawal else serialize(decision).get("effective_for_new_recordings_at") if decision else None,
                       "expires_at": serialize(receipt)["expires_at"]})
    return {"items": output}


@router.post("/consents/{receipt_id}/withdraw")
async def withdraw_consent(receipt_id: str, current_user: dict = Depends(get_current_user)):
    """GOV-001: the caregiver may revoke a receipt without deleting its audit trail."""
    if current_user.get("role") != "user":
        raise HTTPException(status_code=403, detail="caregiver_account_required")
    db = get_database()
    receipt = await db.consent_receipts.find_one({"_id": oid(receipt_id)})
    if not receipt or receipt["child_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=404, detail="consent_receipt_not_found")
    if await db.consent_withdrawals.find_one({"receipt_id": receipt_id}):
        raise HTTPException(status_code=409, detail="consent_already_withdrawn")
    doc = {"receipt_id": receipt_id, "child_id": receipt["child_id"],
           "status": "withdrawn", "withdrawn_by": str(current_user["_id"]),
           "created_at": utc_now()}
    try:
        result = await db.consent_withdrawals.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="consent_already_withdrawn") from exc
    await audit("governance.consent_withdrawn", current_user, target=receipt_id)
    return {"id": str(result.inserted_id), "status": "withdrawn"}


@router.post("/consents/{receipt_id}/verify")
async def verify_consent(
    receipt_id: str, payload: ConsentVerification, current_admin: dict = Depends(require_admin),
):
    """GOV-001: independent administrator attests both external checks."""
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin_required")
    db = get_database()
    receipt = await db.consent_receipts.find_one({"_id": oid(receipt_id)})
    if not receipt:
        raise HTTPException(status_code=404, detail="consent_receipt_not_found")
    if str(current_admin["_id"]) == receipt["submitted_by"]:
        raise HTTPException(status_code=403, detail="independent_verifier_required")
    if not payload.guardian_relationship_verified or not payload.ethics_approval_verified:
        raise HTTPException(status_code=400, detail="external_evidence_not_verified")
    if as_utc(receipt["expires_at"]) <= utc_now():
        raise HTTPException(status_code=400, detail="consent_expired")
    if await db.consent_withdrawals.find_one({"receipt_id": receipt_id}):
        raise HTTPException(status_code=409, detail="consent_withdrawn")
    if await db.consent_decisions.find_one({"receipt_id": receipt_id}):
        raise HTTPException(status_code=409, detail="consent_already_decided")
    verified_at = utc_now()
    effective_at = max(verified_at, as_utc(receipt["valid_from"]))
    doc = {
        "receipt_id": receipt_id, "child_id": receipt["child_id"],
        "status": "verified", "verified_by": str(current_admin["_id"]),
        "guardian_relationship_verified": True, "ethics_approval_verified": True,
        "effective_for_new_recordings_at": effective_at,
        "created_at": verified_at,
    }
    try:
        result = await db.consent_decisions.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="consent_already_decided") from exc
    await audit("governance.consent_verified", current_admin, target=receipt_id,
                meta={"event_id": str(result.inserted_id)})
    return {"id": str(result.inserted_id), "status": "verified",
            "effective_for_new_recordings_at": effective_at.isoformat()}


@router.post("/consents/{receipt_id}/reject")
async def reject_consent(
    receipt_id: str, payload: ConsentRejection, current_admin: dict = Depends(require_admin),
):
    """GOV-001/007: record a real rejected external-evidence review."""
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin_required")
    db = get_database()
    receipt = await db.consent_receipts.find_one({"_id": oid(receipt_id)})
    if not receipt:
        raise HTTPException(status_code=404, detail="consent_receipt_not_found")
    if str(current_admin["_id"]) == receipt["submitted_by"]:
        raise HTTPException(status_code=403, detail="independent_verifier_required")
    if await db.consent_withdrawals.find_one({"receipt_id": receipt_id}):
        raise HTTPException(status_code=409, detail="consent_withdrawn")
    if await db.consent_decisions.find_one({"receipt_id": receipt_id}):
        raise HTTPException(status_code=409, detail="consent_already_decided")
    doc = {
        "receipt_id": receipt_id, "child_id": receipt["child_id"],
        "status": "rejected", "reason_code": payload.reason_code,
        "verified_by": str(current_admin["_id"]), "created_at": utc_now(),
    }
    try:
        result = await db.consent_decisions.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="consent_already_decided") from exc
    await audit("governance.consent_rejected", current_admin, target=receipt_id,
                meta={"reason_code": payload.reason_code})
    return {"id": str(result.inserted_id), "status": "rejected"}


class ReviewItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:/-]+$")
    word_id: str | None = Field(default=None, pattern=r"^TA_WORD_\d{4}$")
    audio_sha256: str | None = Field(default=None, pattern=HASH_PATTERN)
    source_sample_id: str | None = Field(default=None, max_length=128)
    category: Literal["positive", "confusable", "audio_quality_negative"] | None = None
    expected_decision: Literal["PASS", "RETRY", "UNSCORABLE"] | None = None
    content_sha256: str | None = Field(default=None, pattern=HASH_PATTERN)


class BatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Scope
    manifest_sha256: str = Field(pattern=HASH_PATTERN)
    child_id: str | None = None
    active_words: list[str] = Field(default_factory=list, max_length=500)
    forbidden_sample_ids: list[str] = Field(default_factory=list, max_length=100000)
    clinical_sections: dict[str, str] = Field(default_factory=dict)
    items: list[ReviewItemInput] = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def valid_batch(self) -> "BatchInput":
        if len({item.item_id for item in self.items}) != len(self.items):
            raise ValueError("review item IDs must be unique")
        if self.kind == "reference":
            if any(not item.word_id or not item.audio_sha256 for item in self.items):
                raise ValueError("reference items need word and audio hash")
        elif self.kind == "canary":
            if not self.active_words or len(set(self.active_words)) != len(self.active_words):
                raise ValueError("canary active words required")
            if any(not item.word_id or not item.audio_sha256 or not item.source_sample_id
                   or not item.category or not item.expected_decision for item in self.items):
                raise ValueError("canary item metadata incomplete")
            if {item.category for item in self.items} != {"positive", "confusable", "audio_quality_negative"}:
                raise ValueError("canary category coverage incomplete")
            positives = {item.word_id for item in self.items if item.category == "positive"}
            if not set(self.active_words).issubset(positives):
                raise ValueError("canary positive word coverage incomplete")
            if any(item.source_sample_id in self.forbidden_sample_ids for item in self.items):
                raise ValueError("canary source overlaps training or reference")
        else:
            if not self.child_id or len(self.items) != 1 or not self.items[0].content_sha256:
                raise ValueError("clinical batch requires child and one content bundle")
            if set(self.clinical_sections) != CLINICAL_SECTIONS or any(
                not re.fullmatch(HASH_PATTERN, value) for value in self.clinical_sections.values()
            ):
                raise ValueError("clinical content sections incomplete")
            if self.items[0].content_sha256 != clinical_bundle_hash(self.clinical_sections):
                raise ValueError("clinical content bundle hash mismatch")
        return self


class ReviewDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    observed_sha256: str = Field(pattern=HASH_PATTERN)
    decision: Literal["approved", "rejected"]
    capture_valid: bool | None = None
    quality_score: float | None = Field(default=None, ge=0, le=1)


@router.post("/batches")
async def create_batch(payload: BatchInput, current_admin: dict = Depends(require_admin)):
    """GOV-003..005: stage metadata-only candidates; creation is not approval."""
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin_required")
    db = get_database()
    if payload.kind == "clinical":
        child = await db.users.find_one({"_id": oid(payload.child_id)})
        if not child or child.get("role") != "user" or not child.get("therapist_id"):
            raise HTTPException(status_code=409, detail="assigned_therapist_required")
    doc = payload.model_dump()
    doc.update({"status": "pending_review", "created_by": str(current_admin["_id"]),
                "created_at": utc_now()})
    result = await db.review_batches.insert_one(doc)
    await audit("governance.batch_created", current_admin, target=str(result.inserted_id),
                meta={"kind": payload.kind, "count": len(payload.items)})
    return {"id": str(result.inserted_id), "status": "pending_review",
            "kind": payload.kind, "item_count": len(payload.items)}


async def _get_batch(db, batch_id: str) -> dict:
    batch = await db.review_batches.find_one({"_id": oid(batch_id)})
    if not batch:
        raise HTTPException(status_code=404, detail="review_batch_not_found")
    return batch


@router.get("/batches")
async def list_batches(current_user: dict = Depends(get_current_user)):
    """GOV-007: real review queue, filtered by verified scope and relationship."""
    if current_user.get("role") not in {"therapist", "admin"}:
        raise HTTPException(status_code=403, detail="reviewer_required")
    db = get_database()
    rows = await db.review_batches.find({}).to_list(length=200)
    visible = []
    for row in rows:
        if current_user.get("role") == "therapist":
            if not await is_qualified(db, str(current_user["_id"]), row["kind"]):
                continue
            if row["kind"] == "clinical":
                child = await db.users.find_one({"_id": oid(row["child_id"])})
                if not child or child.get("therapist_id") != str(current_user["_id"]):
                    continue
        count = len(await db.review_decisions.find({"batch_id": str(row["_id"])}).to_list(length=5000))
        visible.append({"id": str(row["_id"]), "kind": row["kind"],
                        "manifest_sha256": row["manifest_sha256"],
                        "item_count": len(row["items"]), "reviewed_count": count,
                        "status": "pending_review" if count < len(row["items"]) else "reviewed_pending_export"})
    return {"items": visible}


@router.get("/batches/{batch_id}")
async def get_batch(batch_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    batch = await _get_batch(db, batch_id)
    if current_user.get("role") not in {"therapist", "admin"}:
        raise HTTPException(status_code=403, detail="reviewer_required")
    if current_user.get("role") == "therapist" and not await is_qualified(db, str(current_user["_id"]), batch["kind"]):
        raise HTTPException(status_code=403, detail="verified_reviewer_scope_required")
    if batch["kind"] == "clinical" and current_user.get("role") == "therapist":
        child = await db.users.find_one({"_id": oid(batch["child_id"])})
        if not child or child.get("therapist_id") != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="assigned_therapist_required")
    decisions = await db.review_decisions.find({"batch_id": batch_id}).to_list(length=5000)
    return {"batch": serialize(batch), "decisions": serialize(decisions)}


@router.post("/batches/{batch_id}/decisions")
async def review_item(
    batch_id: str, payload: ReviewDecisionInput, current_user: dict = Depends(get_current_user),
):
    """GOV-003..006: accept only a qualified actor's exact-hash decision."""
    if current_user.get("role") != "therapist":
        raise HTTPException(status_code=403, detail="qualified_therapist_required")
    db = get_database()
    batch = await _get_batch(db, batch_id)
    reviewer_id = str(current_user["_id"])
    if not await is_qualified(db, reviewer_id, batch["kind"]):
        raise HTTPException(status_code=403, detail="verified_reviewer_scope_required")
    if batch["kind"] == "clinical":
        child = await db.users.find_one({"_id": oid(batch["child_id"])})
        if not child or child.get("therapist_id") != reviewer_id:
            raise HTTPException(status_code=403, detail="assigned_therapist_required")
    item = next((row for row in batch["items"] if row["item_id"] == payload.item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="review_item_not_found")
    expected_hash = item.get("content_sha256") if batch["kind"] == "clinical" else item.get("audio_sha256")
    if payload.observed_sha256 != expected_hash:
        raise HTTPException(status_code=409, detail="review_item_hash_mismatch")
    if batch["kind"] == "reference" and payload.decision == "approved":
        if payload.capture_valid is not True or payload.quality_score is None:
            raise HTTPException(status_code=400, detail="reference_quality_review_required")
    if await db.review_decisions.find_one({"batch_id": batch_id, "item_id": payload.item_id}):
        raise HTTPException(status_code=409, detail="review_item_already_decided")
    doc = {
        "batch_id": batch_id, "item_id": payload.item_id, "kind": batch["kind"],
        "observed_sha256": payload.observed_sha256, "decision": payload.decision,
        "capture_valid": payload.capture_valid, "quality_score": payload.quality_score,
        "reviewer_id": reviewer_id, "review_provenance": "qualified_human",
        "created_at": utc_now(),
    }
    try:
        result = await db.review_decisions.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="review_item_already_decided") from exc
    await audit("governance.item_reviewed", current_user, target=batch_id,
                meta={"item_id": payload.item_id, "decision": payload.decision})
    return serialize(dict(doc, _id=result.inserted_id))


@router.get("/batches/{batch_id}/export")
async def export_batch(batch_id: str, current_admin: dict = Depends(require_admin)):
    """GOV-003..005: emit exact-source metadata only after all human decisions."""
    if current_admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin_required")
    db = get_database()
    batch = await _get_batch(db, batch_id)
    decisions = await db.review_decisions.find({"batch_id": batch_id}).to_list(length=5000)
    by_item = {row["item_id"]: row for row in decisions}
    if len(by_item) != len(batch["items"]):
        raise HTTPException(status_code=409, detail="review_batch_incomplete")
    for row in decisions:
        if not await is_qualified(db, row["reviewer_id"], batch["kind"]):
            raise HTTPException(status_code=409, detail="reviewer_qualification_revoked")
    if batch["kind"] == "reference":
        approvals = []
        for item in batch["items"]:
            decision = by_item[item["item_id"]]
            approvals.append({
                "sample_id": item["item_id"], "canonical_word_id": item["word_id"],
                "audio_sha256": item["audio_sha256"],
                "approved": decision["decision"] == "approved",
                "capture_valid": decision["capture_valid"],
                "quality_score": decision["quality_score"],
                "review_provenance": "qualified_human", "reviewer_qualified": True,
                "reviewer_id": decision["reviewer_id"],
            })
        result = {"schema_version": "vaakmitra-reference-approvals-1",
                  "dataset_manifest_hash": batch["manifest_sha256"],
                  "human_approved": True, "approvals": approvals}
        return _sign_export(result)
    if any(row["decision"] != "approved" for row in decisions):
        raise HTTPException(status_code=409, detail="review_batch_rejected")
    if batch["kind"] == "clinical":
        child = await db.users.find_one({"_id": oid(batch["child_id"])})
        if not child or child.get("therapist_id") != decisions[0]["reviewer_id"]:
            raise HTTPException(status_code=409, detail="therapist_relationship_changed")
    result = {"schema_version": "vaakmitra-review-export-1", "kind": batch["kind"],
              "manifest_sha256": batch["manifest_sha256"], "human_approved": True,
              "items": [{**item, "reviewer_id": by_item[item["item_id"]]["reviewer_id"],
                         "observed_sha256": by_item[item["item_id"]]["observed_sha256"]}
                        for item in batch["items"]]}
    return _sign_export(result)


def _sign_export(payload: dict) -> dict:
    key = os.environ.get("VAAKMITRA_REVIEW_SIGNING_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="review_signing_key_unavailable")
    try:
        return sign_review_export(payload, key)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="review_signing_key_invalid") from exc
