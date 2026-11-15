"""DEC-019/GOV-001..006: actor identity, evidence, and approvals are not AI flags."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.routers import governance


CAREGIVER = {"_id": ObjectId("0000000000000000000000c1"), "role": "user"}
THERAPIST = {"_id": ObjectId("0000000000000000000000d1"), "role": "therapist"}
ADMIN = {"_id": ObjectId("0000000000000000000000a1"), "role": "admin"}


class Rows:
    def __init__(self, docs=()):
        self.docs = list(docs)

    async def find_one(self, query, **kwargs):
        matches = [row for row in self.docs if all(row.get(k) == v for k, v in query.items())]
        if kwargs.get("sort"):
            key = kwargs["sort"][0][0]
            matches.sort(key=lambda row: row.get(key), reverse=True)
        return matches[0] if matches else None

    async def insert_one(self, doc):
        saved = dict(doc, _id=ObjectId())
        self.docs.append(saved)
        return SimpleNamespace(inserted_id=saved["_id"])

    def find(self, query):
        matches = [row for row in self.docs if all(row.get(k) == v for k, v in query.items())]

        class Cursor:
            async def to_list(self, length):
                return matches[:length]

        return Cursor()


class Database:
    def __init__(self):
        self.users = Rows([CAREGIVER, THERAPIST, ADMIN])
        self.reviewer_credentials = Rows()
        self.consent_receipts = Rows()
        self.consent_decisions = Rows()
        self.consent_withdrawals = Rows()
        self.review_batches = Rows()
        self.review_decisions = Rows()


@pytest.fixture
def database(monkeypatch):
    db = Database()
    monkeypatch.setattr(governance, "get_database", lambda: db)

    async def no_audit(*args, **kwargs):
        return None

    monkeypatch.setattr(governance, "audit", no_audit)
    monkeypatch.setenv("VAAKMITRA_REVIEW_SIGNING_KEY", "test-review-key-with-at-least-32-characters")
    return db


@pytest.mark.asyncio
async def test_gov002_self_registered_therapist_cannot_verify_self(database):
    request = governance.CredentialInput(
        therapist_id=str(THERAPIST["_id"]), scope="reference",
        evidence_sha256="a" * 64, external_ref="credential-check-1",
    )
    with pytest.raises(HTTPException) as error:
        await governance.verify_credential(request, THERAPIST)
    assert error.value.status_code == 403
    assert database.reviewer_credentials.docs == []


@pytest.mark.asyncio
async def test_gov002_admin_verification_is_scoped_and_revocable(database):
    request = governance.CredentialInput(
        therapist_id=str(THERAPIST["_id"]), scope="reference",
        evidence_sha256="a" * 64, external_ref="credential-check-1",
    )
    await governance.verify_credential(request, ADMIN)
    assert await governance.is_qualified(database, str(THERAPIST["_id"]), "reference") is True
    assert await governance.is_qualified(database, str(THERAPIST["_id"]), "clinical") is False
    await governance.revoke_credential(str(THERAPIST["_id"]), "reference", ADMIN)
    assert await governance.is_qualified(database, str(THERAPIST["_id"]), "reference") is False


@pytest.mark.asyncio
async def test_gov001_caregiver_receipt_is_pending_until_distinct_admin_verifies(database):
    start = datetime.now(timezone.utc) - timedelta(days=1)
    request = governance.ConsentInput(
        protocol_id="validation-v1", purpose="child_validation",
        guardian_document_sha256="b" * 64,
        ethics_approval_id="ethics-review-1", ethics_document_sha256="c" * 64,
        valid_from=start, expires_at=start + timedelta(days=365),
    )
    receipt = await governance.submit_consent(request, CAREGIVER)
    assert receipt["status"] == "pending_verification"
    assert receipt["effective_for_new_recordings_at"] is None
    with pytest.raises(HTTPException) as error:
        await governance.verify_consent(receipt["id"], governance.ConsentVerification(guardian_relationship_verified=True, ethics_approval_verified=True), CAREGIVER)
    assert error.value.status_code == 403
    verified = await governance.verify_consent(receipt["id"], governance.ConsentVerification(guardian_relationship_verified=True, ethics_approval_verified=True), ADMIN)
    assert verified["status"] == "verified"
    assert datetime.fromisoformat(verified["effective_for_new_recordings_at"]) >= start


@pytest.mark.asyncio
async def test_gov001_caregiver_can_withdraw_verified_consent(database):
    start = datetime.now(timezone.utc)
    receipt = await governance.submit_consent(governance.ConsentInput(
        protocol_id="validation-v1", purpose="child_validation",
        guardian_document_sha256="b" * 64, ethics_approval_id="ethics-review-1",
        ethics_document_sha256="c" * 64, valid_from=start,
        expires_at=start + timedelta(days=365),
    ), CAREGIVER)
    await governance.verify_consent(receipt["id"], governance.ConsentVerification(
        guardian_relationship_verified=True, ethics_approval_verified=True), ADMIN)
    withdrawn = await governance.withdraw_consent(receipt["id"], CAREGIVER)
    assert withdrawn["status"] == "withdrawn"
    listed = await governance.my_consents(CAREGIVER)
    assert listed["items"][0]["status"] == "withdrawn"
    with pytest.raises(HTTPException) as duplicate:
        await governance.withdraw_consent(receipt["id"], CAREGIVER)
    assert duplicate.value.status_code == 409


@pytest.mark.asyncio
async def test_gov001_rejected_consent_is_visible_and_cannot_be_verified(database):
    start = datetime.now(timezone.utc)
    receipt = await governance.submit_consent(governance.ConsentInput(
        protocol_id="validation-v1", purpose="child_validation",
        guardian_document_sha256="b" * 64, ethics_approval_id="ethics-review-1",
        ethics_document_sha256="c" * 64, valid_from=start,
        expires_at=start + timedelta(days=365),
    ), CAREGIVER)
    rejected = await governance.reject_consent(receipt["id"], governance.ConsentRejection(
        reason_code="document_mismatch"), ADMIN)
    assert rejected["status"] == "rejected"
    listed = await governance.my_consents(CAREGIVER)
    assert listed["items"][0]["status"] == "rejected"
    with pytest.raises(HTTPException) as error:
        await governance.verify_consent(receipt["id"], governance.ConsentVerification(
            guardian_relationship_verified=True, ethics_approval_verified=True), ADMIN)
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_gov001_missing_ethics_evidence_cannot_be_verified(database):
    with pytest.raises(ValueError):
        governance.ConsentInput(
            protocol_id="validation-v1", purpose="child_validation",
            guardian_document_sha256="b" * 64,
            ethics_approval_id="", ethics_document_sha256="c" * 64,
            valid_from=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )


@pytest.mark.asyncio
async def test_gov001_mongo_naive_utc_dates_do_not_crash_verification(database):
    start = datetime.now(timezone.utc)
    receipt = await governance.submit_consent(governance.ConsentInput(
        protocol_id="validation-v1", purpose="child_validation",
        guardian_document_sha256="b" * 64, ethics_approval_id="ethics-review-1",
        ethics_document_sha256="c" * 64, valid_from=start,
        expires_at=start + timedelta(days=365),
    ), CAREGIVER)
    database.consent_receipts.docs[0]["valid_from"] = start.replace(tzinfo=None)
    database.consent_receipts.docs[0]["expires_at"] = (start + timedelta(days=365)).replace(tzinfo=None)
    verified = await governance.verify_consent(receipt["id"], governance.ConsentVerification(
        guardian_relationship_verified=True, ethics_approval_verified=True), ADMIN)
    assert verified["status"] == "verified"


def _reference_batch():
    return governance.BatchInput(
        kind="reference", manifest_sha256="d" * 64,
        items=[governance.ReviewItemInput(
            item_id="source-1", word_id="TA_WORD_0001", audio_sha256="a" * 64,
        )],
    )


@pytest.mark.asyncio
async def test_gov003_unqualified_actor_cannot_approve_reference(database):
    batch = await governance.create_batch(_reference_batch(), ADMIN)
    request = governance.ReviewDecisionInput(
        item_id="source-1", observed_sha256="a" * 64,
        decision="approved", capture_valid=True, quality_score=0.8,
    )
    with pytest.raises(HTTPException) as error:
        await governance.review_item(batch["id"], request, THERAPIST)
    assert error.value.status_code == 403
    assert database.review_decisions.docs == []


@pytest.mark.asyncio
async def test_gov003_reference_export_binds_real_actor_and_exact_sample(database):
    batch = await governance.create_batch(_reference_batch(), ADMIN)
    with pytest.raises(HTTPException) as error:
        await governance.export_batch(batch["id"], ADMIN)
    assert error.value.status_code == 409
    await governance.verify_credential(governance.CredentialInput(
        therapist_id=str(THERAPIST["_id"]), scope="reference",
        evidence_sha256="f" * 64, external_ref="credential-check-1",
    ), ADMIN)
    with pytest.raises(HTTPException) as changed:
        await governance.review_item(batch["id"], governance.ReviewDecisionInput(
            item_id="source-1", observed_sha256="e" * 64,
            decision="approved", capture_valid=True, quality_score=0.8,
        ), THERAPIST)
    assert changed.value.status_code == 409
    await governance.review_item(batch["id"], governance.ReviewDecisionInput(
        item_id="source-1", observed_sha256="a" * 64,
        decision="approved", capture_valid=True, quality_score=0.8,
    ), THERAPIST)
    exported = await governance.export_batch(batch["id"], ADMIN)
    assert exported["human_approved"] is True
    assert exported["dataset_manifest_hash"] == "d" * 64
    assert exported["approvals"] == [{
        "sample_id": "source-1", "canonical_word_id": "TA_WORD_0001",
        "audio_sha256": "a" * 64, "approved": True, "capture_valid": True,
        "quality_score": 0.8, "review_provenance": "qualified_human",
        "reviewer_qualified": True, "reviewer_id": str(THERAPIST["_id"]),
    }]
    await governance.revoke_credential(str(THERAPIST["_id"]), "reference", ADMIN)
    with pytest.raises(HTTPException) as revoked:
        await governance.export_batch(batch["id"], ADMIN)
    assert revoked.value.status_code == 409


def test_gov004_canary_batch_needs_categories_and_positive_word_coverage():
    with pytest.raises(ValueError):
        governance.BatchInput(
            kind="canary", manifest_sha256="d" * 64,
            active_words=["TA_WORD_0001"],
            items=[governance.ReviewItemInput(
                item_id="canary-1", word_id="TA_WORD_0001",
                audio_sha256="a" * 64, category="positive",
                expected_decision="PASS", source_sample_id="sample-1",
            )],
        )


def test_gov005_clinical_batch_cannot_omit_required_content_sections():
    with pytest.raises(ValueError):
        governance.BatchInput(
            kind="clinical", manifest_sha256="d" * 64,
            child_id=str(CAREGIVER["_id"]),
            items=[governance.ReviewItemInput(item_id="content-bundle", content_sha256="a" * 64)],
            clinical_sections={"vocabulary": "a" * 64},
        )


def test_gov005_clinical_batch_accepts_exact_required_sections():
    sections = {name: "a" * 64 for name in governance.CLINICAL_SECTIONS}
    batch = governance.BatchInput(
        kind="clinical", manifest_sha256="d" * 64,
        child_id=str(CAREGIVER["_id"]),
        items=[governance.ReviewItemInput(item_id="content-bundle", content_sha256=governance.clinical_bundle_hash(sections))],
        clinical_sections=sections,
    )
    assert batch.clinical_sections == sections


def test_gov005_clinical_bundle_hash_must_bind_all_sections():
    sections = {name: "a" * 64 for name in governance.CLINICAL_SECTIONS}
    with pytest.raises(ValueError):
        governance.BatchInput(
            kind="clinical", manifest_sha256="d" * 64,
            child_id=str(CAREGIVER["_id"]),
            items=[governance.ReviewItemInput(item_id="content-bundle", content_sha256="a" * 64)],
            clinical_sections=sections,
        )


@pytest.mark.asyncio
async def test_gov005_clinical_approval_requires_assigned_qualified_therapist(database):
    database.users.docs[0] = dict(CAREGIVER, therapist_id=str(THERAPIST["_id"]))
    sections = {name: "a" * 64 for name in governance.CLINICAL_SECTIONS}
    batch = await governance.create_batch(governance.BatchInput(
        kind="clinical", manifest_sha256="d" * 64,
        child_id=str(CAREGIVER["_id"]),
        items=[governance.ReviewItemInput(item_id="content-bundle", content_sha256=governance.clinical_bundle_hash(sections))],
        clinical_sections=sections,
    ), ADMIN)
    await governance.verify_credential(governance.CredentialInput(
        therapist_id=str(THERAPIST["_id"]), scope="clinical",
        evidence_sha256="f" * 64, external_ref="credential-check-2",
    ), ADMIN)
    result = await governance.review_item(batch["id"], governance.ReviewDecisionInput(
        item_id="content-bundle", observed_sha256=governance.clinical_bundle_hash(sections), decision="approved",
    ), THERAPIST)
    assert result["reviewer_id"] == str(THERAPIST["_id"])
