from __future__ import annotations

import pytest
from modeling.inventory.consensus import (
    AllophoneRule,
    InventorySource,
    build_candidate_inventory,
    evaluate_inventory_coverage,
    load_inventory_sources,
    map_acoustic_units,
)

SOURCE_CONFIG = "modeling/configs/tamil_phoneme_sources.json"


def _source(source_id: str, segments: tuple[str, ...]) -> InventorySource:
    return InventorySource(
        source_id=source_id,
        revision="a" * 40,
        source_scope="published_inventory",
        segments=segments,
    )


def test_consensus_keeps_blank_first_and_reports_source_disagreement() -> None:
    result = build_candidate_inventory(
        sources=(
            _source("phoible-a", ("a", "m")),
            _source("phoible-b", ("a", "n")),
        ),
        observed_units=("a", "m", "n", "x"),
        allophones=(AllophoneRule(source="ŋ", canonical="n", provenance="fixture"),),
        version="ta-candidate-1",
    )

    assert result.tokens == ("<blank>", "a", "m", "n", "x")
    assert result.core_tokens == ("a",)
    assert result.extended_tokens == ("m", "n", "x")
    disagreement = next(conflict for conflict in result.conflicts if conflict.token == "m")
    assert disagreement.present_in == ("phoible-a",)
    assert disagreement.missing_from == ("phoible-b",)
    assert result.allophones[0].source == "ŋ"
    assert result.expert_approved is False
    assert result.production_ready is False


def test_consensus_is_stable_across_source_and_segment_order() -> None:
    first = build_candidate_inventory(
        sources=(_source("b", ("m", "a")), _source("a", ("n", "a"))),
        observed_units=("n", "a", "m"),
        allophones=(),
        version="v1",
    )
    second = build_candidate_inventory(
        sources=(_source("a", ("a", "n")), _source("b", ("a", "m"))),
        observed_units=("m", "n", "a"),
        allophones=(),
        version="v1",
    )

    assert first.digest() == second.digest()
    assert first.token_provenance == second.token_provenance


def test_coverage_reports_unknown_units_without_silent_mapping() -> None:
    inventory = build_candidate_inventory(
        sources=(_source("published", ("a", "m")),),
        observed_units=("a", "m"),
        allophones=(AllophoneRule(source="ɱ", canonical="m", provenance="fixture"),),
        version="v1",
    )

    report = evaluate_inventory_coverage(inventory, (("a", "ɱ"), ("a", "q")))

    assert report.total_units == 4
    assert report.known_units == 3
    assert report.unknown_units == ("q",)
    assert report.coverage == pytest.approx(0.75)
    with pytest.raises(ValueError, match="unresolved phoneme: q"):
        map_acoustic_units(inventory, ("a", "q"))


def test_allophone_mapping_is_explicit_and_canonical_target_must_exist() -> None:
    inventory = build_candidate_inventory(
        sources=(_source("published", ("a", "m")),),
        observed_units=("a", "m"),
        allophones=(AllophoneRule(source="ɱ", canonical="m", provenance="fixture"),),
        version="v1",
    )

    assert map_acoustic_units(inventory, ("a", "ɱ")) == ("a", "m")
    with pytest.raises(ValueError, match="canonical allophone target"):
        build_candidate_inventory(
            sources=(_source("published", ("a",)),),
            observed_units=("a",),
            allophones=(AllophoneRule(source="ɱ", canonical="m", provenance="fixture"),),
            version="v1",
        )


def test_pinned_tamil_source_catalog_contains_three_phoible_inventories() -> None:
    sources = load_inventory_sources(SOURCE_CONFIG)

    assert tuple(source.source_id for source in sources) == (
        "phoible-tamil-1058",
        "phoible-tamil-1788",
        "phoible-tamil-2611",
    )
    assert tuple(len(source.segments) for source in sources) == (33, 43, 36)
    assert {source.revision for source in sources} == {
        "9cfbaa67713722a2726a439202562efe8f305b9f"
    }


@pytest.mark.parametrize(
    ("sources", "observed", "message"),
    [
        ((), ("a",), "source"),
        ((_source("published", ("a",)),), (), "observed"),
        (
            (_source("published", ("a",)),),
            ("a", "<blank>"),
            "blank",
        ),
    ],
)
def test_consensus_rejects_incomplete_or_colliding_inputs(
    sources: tuple[InventorySource, ...],
    observed: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_candidate_inventory(
            sources=sources,
            observed_units=observed,
            allophones=(),
            version="v1",
        )
