from __future__ import annotations

from modeling.calibration.controlled_confusions import (
    PhonemeFeatures,
    generate_controlled_confusions,
)


def _features() -> dict[str, PhonemeFeatures]:
    return {
        "a": PhonemeFeatures(
            token="a", phonological_class="vowel", place="open", manner="vowel", voiced=True
        ),
        "a\u02d0": PhonemeFeatures(
            token="a\u02d0",
            phonological_class="vowel",
            place="open",
            manner="vowel",
            voiced=True,
        ),
        "m": PhonemeFeatures(
            token="m", phonological_class="nasal", place="bilabial", manner="nasal", voiced=True
        ),
        "n": PhonemeFeatures(
            token="n", phonological_class="nasal", place="alveolar", manner="nasal", voiced=True
        ),
    }


def test_confusions_cover_substitution_length_gemination_and_sequence_edits() -> None:
    original = ("a", "m", "n")

    generated = generate_controlled_confusions(
        original,
        feature_map=_features(),
        length_pairs={"a": "a\u02d0", "a\u02d0": "a"},
        geminatable=frozenset({"m", "n"}),
    )

    kinds = {item.kind for item in generated}
    assert kinds == {
        "substitution",
        "length",
        "gemination",
        "insertion",
        "deletion",
        "transposition",
    }
    assert original == ("a", "m", "n")
    assert all(item.corrupted != item.original for item in generated)
    assert all(item.reason for item in generated)


def test_substitution_selects_nearest_feature_competitor_deterministically() -> None:
    generated = generate_controlled_confusions(
        ("m",),
        feature_map=_features(),
        length_pairs={},
        geminatable=frozenset(),
    )
    substitution = next(item for item in generated if item.kind == "substitution")

    assert substitution.expected == "m"
    assert substitution.replacement == "n"
    assert substitution.corrupted == ("n",)


def test_unknown_sequence_phone_is_reported_instead_of_guessed() -> None:
    try:
        generate_controlled_confusions(
            ("q",),
            feature_map=_features(),
            length_pairs={},
            geminatable=frozenset(),
        )
    except ValueError as error:
        assert "unknown phoneme: q" in str(error)
    else:
        raise AssertionError("unknown phone was silently accepted")
