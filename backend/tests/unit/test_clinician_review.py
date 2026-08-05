from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from modeling.inventory.clinician_review import (
    ClinicianReviewPacket,
    create_review_template,
    finalize_expert_inventory,
)
from modeling.inventory.consensus import (
    AllophoneRule,
    CandidateInventory,
    InventorySource,
    build_candidate_inventory,
)

_LONG_A = "a\u02d0"
_LABIODENTAL_NASAL = "\u0271"


def _candidate() -> CandidateInventory:
    return build_candidate_inventory(
        sources=(
            InventorySource(
                source_id="published-a",
                revision="a" * 40,
                source_scope="published_inventory",
                segments=("a", _LONG_A, "m", "q"),
            ),
        ),
        observed_units=("a", _LONG_A, "m", "q"),
        allophones=(
            AllophoneRule(
                source=_LABIODENTAL_NASAL,
                canonical="m",
                provenance="published-a",
            ),
        ),
        version="ta-candidate-1",
    )


def _completed_payload() -> dict[str, Any]:
    candidate = _candidate()
    payload = create_review_template(candidate).model_dump(mode="json")
    for item in payload["token_reviews"]:
        item["decision"] = "approve"
        item["notes"] = "Reviewed against Tamil contrast and corpus examples."
    payload["token_reviews"][-1].update(
        {"decision": "replace", "replacement_token": "k", "notes": "Corrected token."}
    )
    for item in payload["allophone_reviews"]:
        item["decision"] = "approve"
        item["notes"] = "Accepted as an explicit acoustic mapping."
    payload["policies"] = {
        "vowel_length": "contrastive_separate_length_mark",
        "gemination": "contrastive_repeated_consonant",
        "allophones": "explicit_reviewed_mappings_only",
        "unknown_phone": "unscorable_fail_closed",
    }
    payload["reviewer"] = {
        "role": "tamil_linguist",
        "organization": "Example review organization",
        "reviewed_at": "2026-08-05T14:00:00Z",
        "attests_inventory_reviewed": True,
    }
    return payload


def test_template_binds_candidate_and_lists_every_reviewable_item() -> None:
    candidate = _candidate()

    packet = create_review_template(candidate)

    assert packet.candidate_digest == candidate.digest()
    assert tuple(item.token for item in packet.token_reviews) == candidate.tokens[1:]
    assert {item.decision for item in packet.token_reviews} == {"pending"}
    assert tuple(item.source for item in packet.allophone_reviews) == (
        _LABIODENTAL_NASAL,
    )
    assert packet.reviewer is None


def test_completed_attested_review_produces_expert_contract_but_not_production_claim() -> None:
    candidate = _candidate()
    packet = ClinicianReviewPacket.model_validate(_completed_payload())

    approved = finalize_expert_inventory(candidate, packet)

    assert approved.tokens == ("<blank>", "a", _LONG_A, "k", "m")
    assert approved.allophones[0].source == _LABIODENTAL_NASAL
    assert approved.allophones[0].canonical == "m"
    assert approved.vowel_length_policy == "contrastive_separate_length_mark"
    assert approved.gemination_policy == "contrastive_repeated_consonant"
    assert approved.unknown_phone_policy == "unscorable_fail_closed"
    assert approved.expert_approved is True
    assert approved.production_ready is False
    assert approved.evidence_scope == "expert_reviewed_inventory_not_clinically_validated"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload.update(candidate_digest="0" * 64), "digest"),
        (
            lambda payload: payload["token_reviews"][0].update(decision="pending"),
            "pending",
        ),
        (
            lambda payload: payload["policies"].update(vowel_length="needs_discussion"),
            "policy",
        ),
        (lambda payload: payload.update(reviewer=None), "reviewer"),
    ],
)
def test_finalization_fails_closed_on_incomplete_or_unbound_review(
    mutation: Callable[[dict[str, Any]], None], message: str
) -> None:
    candidate = _candidate()
    payload = deepcopy(_completed_payload())
    mutation(payload)
    packet = ClinicianReviewPacket.model_validate(payload)

    with pytest.raises(ValueError, match=message):
        finalize_expert_inventory(candidate, packet)


def test_finalization_rejects_missing_duplicate_and_invalid_replacements() -> None:
    candidate = _candidate()
    payload = _completed_payload()
    payload["token_reviews"] = payload["token_reviews"][:-1]
    packet = ClinicianReviewPacket.model_validate(payload)
    with pytest.raises(ValueError, match="exactly cover"):
        finalize_expert_inventory(candidate, packet)

    payload = _completed_payload()
    payload["token_reviews"][0]["token"] = "m"
    packet = ClinicianReviewPacket.model_validate(payload)
    with pytest.raises(ValueError, match="exactly cover"):
        finalize_expert_inventory(candidate, packet)

    payload = _completed_payload()
    payload["token_reviews"][-1]["replacement_token"] = "<blank>"
    with pytest.raises(ValueError, match="blank"):
        ClinicianReviewPacket.model_validate(payload)


def test_cli_writes_exclusive_review_template_and_approved_contract(
    tmp_path: Path,
) -> None:
    from modeling.inventory.build_review_packet import main

    candidate = _candidate()
    candidate_path = tmp_path / "candidate.json"
    review_path = tmp_path / "review.json"
    completed_path = tmp_path / "completed.json"
    approved_path = tmp_path / "approved.json"
    candidate_path.write_text(
        json.dumps(candidate.as_dict(), ensure_ascii=False), encoding="utf-8"
    )

    assert main(
        ["template", "--candidate", str(candidate_path), "--output", str(review_path)]
    ) == 0
    assert json.loads(review_path.read_text(encoding="utf-8"))["review_status"] == (
        "pending_expert_review"
    )
    with pytest.raises(ValueError, match="exists"):
        main(
            [
                "template",
                "--candidate",
                str(candidate_path),
                "--output",
                str(review_path),
            ]
        )

    completed_path.write_text(
        json.dumps(_completed_payload(), ensure_ascii=False), encoding="utf-8"
    )
    assert main(
        [
            "finalize",
            "--candidate",
            str(candidate_path),
            "--review",
            str(completed_path),
            "--output",
            str(approved_path),
        ]
    ) == 0
    approved = json.loads(approved_path.read_text(encoding="utf-8"))
    assert approved["expert_approved"] is True
    assert approved["production_ready"] is False
