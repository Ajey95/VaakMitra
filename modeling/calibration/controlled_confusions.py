"""Deterministic expected-sequence corruptions for proxy pronunciation calibration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConfusionKind = Literal[
    "substitution", "length", "gemination", "insertion", "deletion", "transposition"
]


class PhonemeFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str = Field(min_length=1)
    phonological_class: str = Field(min_length=1)
    place: str = Field(min_length=1)
    manner: str = Field(min_length=1)
    voiced: bool


class ControlledConfusion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ConfusionKind
    original: tuple[str, ...] = Field(min_length=1)
    corrupted: tuple[str, ...] = Field(min_length=1)
    index: int = Field(ge=0)
    expected: str = Field(min_length=1)
    replacement: str | None
    reason: str = Field(min_length=1)


def _feature_distance(first: PhonemeFeatures, second: PhonemeFeatures) -> int:
    return (
        4 * int(first.phonological_class != second.phonological_class)
        + int(first.place != second.place)
        + int(first.manner != second.manner)
        + int(first.voiced != second.voiced)
    )


def _nearest_competitor(
    token: str, feature_map: Mapping[str, PhonemeFeatures]
) -> str:
    source = feature_map[token]
    candidates = [candidate for candidate in feature_map.values() if candidate.token != token]
    if not candidates:
        raise ValueError(f"phoneme has no feature competitor: {token}")
    return min(candidates, key=lambda item: (_feature_distance(source, item), item.token)).token


def generate_controlled_confusions(
    sequence: Sequence[str],
    *,
    feature_map: Mapping[str, PhonemeFeatures],
    length_pairs: Mapping[str, str],
    geminatable: AbstractSet[str],
) -> tuple[ControlledConfusion, ...]:
    """Create known target/acoustic mismatches without synthesizing clinical errors."""

    original = tuple(sequence)
    if not original:
        raise ValueError("phoneme sequence must be non-empty")
    for token in original:
        if token not in feature_map:
            raise ValueError(f"unknown phoneme: {token}")

    generated: list[ControlledConfusion] = []
    for index, token in enumerate(original):
        competitor = _nearest_competitor(token, feature_map)
        substituted = (*original[:index], competitor, *original[index + 1 :])
        generated.append(
            ControlledConfusion(
                kind="substitution",
                original=original,
                corrupted=substituted,
                index=index,
                expected=token,
                replacement=competitor,
                reason="nearest_feature_space_competitor",
            )
        )
        length_competitor = length_pairs.get(token)
        if length_competitor is not None:
            if length_competitor not in feature_map:
                raise ValueError("length-pair replacement is absent from feature_map")
            generated.append(
                ControlledConfusion(
                    kind="length",
                    original=original,
                    corrupted=(*original[:index], length_competitor, *original[index + 1 :]),
                    index=index,
                    expected=token,
                    replacement=length_competitor,
                    reason="short_long_vowel_target_swap",
                )
            )
        if token in geminatable:
            generated.append(
                ControlledConfusion(
                    kind="gemination",
                    original=original,
                    corrupted=(*original[:index], token, *original[index:]),
                    index=index,
                    expected=token,
                    replacement=token,
                    reason="insert_repeated_consonant_target",
                )
            )
        generated.append(
            ControlledConfusion(
                kind="insertion",
                original=original,
                corrupted=(*original[: index + 1], competitor, *original[index + 1 :]),
                index=index,
                expected=token,
                replacement=competitor,
                reason="insert_competing_phone_target",
            )
        )
        if len(original) > 1:
            generated.append(
                ControlledConfusion(
                    kind="deletion",
                    original=original,
                    corrupted=(*original[:index], *original[index + 1 :]),
                    index=index,
                    expected=token,
                    replacement=None,
                    reason="delete_expected_phone_target",
                )
            )
    for index in range(len(original) - 1):
        if original[index] == original[index + 1]:
            continue
        transposed = list(original)
        transposed[index], transposed[index + 1] = transposed[index + 1], transposed[index]
        generated.append(
            ControlledConfusion(
                kind="transposition",
                original=original,
                corrupted=tuple(transposed),
                index=index,
                expected=original[index],
                replacement=original[index + 1],
                reason="transpose_adjacent_phone_targets",
            )
        )
    unique: dict[tuple[str, tuple[str, ...], int], ControlledConfusion] = {}
    for item in generated:
        unique[(item.kind, item.corrupted, item.index)] = item
    return tuple(
        sorted(unique.values(), key=lambda item: (item.kind, item.index, item.corrupted))
    )
