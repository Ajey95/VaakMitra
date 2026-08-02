"""Duration-weighted aggregation from phoneme evidence to known syllables."""

from __future__ import annotations

from vaakmitra.contracts.alignment import AlignedPhoneme, SyllableDefinition
from vaakmitra.contracts.scoring import PhonemeScore, ScoreStatus, SyllableScore
from vaakmitra.scoring.confidence import ScoringConfig, classify_score


def aggregate_syllables(
    phoneme_scores: tuple[PhonemeScore, ...],
    aligned_phonemes: tuple[AlignedPhoneme, ...],
    syllables: tuple[SyllableDefinition, ...],
    config: ScoringConfig,
) -> tuple[SyllableScore, ...]:
    """Aggregate without concealing unscorable constituent evidence."""

    if len(phoneme_scores) != len(aligned_phonemes):
        raise ValueError("phoneme score and alignment lengths must match")
    results: list[SyllableScore] = []
    for syllable in syllables:
        if any(index >= len(phoneme_scores) for index in syllable.phoneme_indices):
            raise ValueError("syllable phoneme index out of range")
        weights = tuple(
            aligned_phonemes[index].end_frame - aligned_phonemes[index].start_frame
            for index in syllable.phoneme_indices
        )
        total_weight = sum(weights)
        score = sum(
            phoneme_scores[index].gop * weight
            for index, weight in zip(syllable.phoneme_indices, weights, strict=True)
        ) / total_weight
        confidence = sum(
            phoneme_scores[index].confidence * weight
            for index, weight in zip(syllable.phoneme_indices, weights, strict=True)
        ) / total_weight
        status: ScoreStatus
        if any(phoneme_scores[index].status == "unscorable" for index in syllable.phoneme_indices):
            status = "unscorable"
        else:
            status = classify_score(score, confidence, config)
        results.append(
            SyllableScore(
                syllable=syllable.text,
                score=score,
                confidence=confidence,
                status=status,
                phoneme_indices=syllable.phoneme_indices,
            )
        )
    return tuple(results)
