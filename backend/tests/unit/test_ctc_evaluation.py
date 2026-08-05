from __future__ import annotations

import json

import pytest
from modeling.evaluation.ctc_metrics import (
    EvaluationRecord,
    collapse_ctc_tokens,
    edit_distance,
    evaluate_records,
)
from modeling.evaluation.evaluate_jsonl import main


def _record(
    reference: tuple[str, ...],
    predicted_tokens: tuple[str, ...],
    *,
    utterance_id: str = "utt-1",
    scorable: bool = True,
    population: str = "adult_tamil_proxy",
    evidence_scope: str = "engineering_proxy",
) -> EvaluationRecord:
    return EvaluationRecord(
        utterance_id=utterance_id,
        reference=reference,
        predicted_tokens=predicted_tokens,
        blank_token="<blank>",
        population=population,
        evidence_scope=evidence_scope,
        scorable=scorable,
    )


def test_ctc_collapse_removes_blanks_and_collapses_only_adjacent_repeats() -> None:
    collapsed = collapse_ctc_tokens(
        ("<blank>", "a", "a", "<blank>", "a", "m", "m"),
        "<blank>",
    )

    assert collapsed == ("a", "a", "m")


@pytest.mark.parametrize(
    ("reference", "hypothesis", "expected"),
    [
        (("a", "m"), ("a", "n"), 1),
        (("a", "m"), ("a",), 1),
        (("a",), ("a", "m"), 1),
        (("a", "m"), ("a", "m"), 0),
    ],
)
def test_edit_distance_counts_literal_phoneme_errors(
    reference: tuple[str, ...],
    hypothesis: tuple[str, ...],
    expected: int,
) -> None:
    assert edit_distance(reference, hypothesis) == expected


def test_evaluation_reports_literal_micro_macro_and_exact_metrics() -> None:
    report = evaluate_records(
        (
            _record(("a", "m"), ("a", "n"), utterance_id="utt-1"),
            _record(("a",), ("a",), utterance_id="utt-2"),
        )
    )

    assert report.record_count == 2
    assert report.scorable_count == 2
    assert report.total_errors == 1
    assert report.reference_tokens == 3
    assert report.micro_per == pytest.approx(1 / 3)
    assert report.macro_per == pytest.approx(0.25)
    assert report.exact_sequence_accuracy == pytest.approx(0.5)
    assert report.unscorable_rate == pytest.approx(0.0)
    assert report.validation_status == "engineering_proxy_only"


def test_evaluation_accounts_for_unscorable_records_without_scoring_them() -> None:
    report = evaluate_records(
        (
            _record(("a",), ("a",), utterance_id="utt-1"),
            _record(("m",), (), utterance_id="utt-2", scorable=False),
        )
    )

    assert report.record_count == 2
    assert report.scorable_count == 1
    assert report.unscorable_count == 1
    assert report.unscorable_rate == pytest.approx(0.5)
    assert report.reference_tokens == 1


def test_evaluation_rejects_mixed_population_or_evidence_scope() -> None:
    adult = _record(("a",), ("a",), utterance_id="adult")
    child = _record(
        ("a",),
        ("a",),
        utterance_id="child",
        population="general_child_proxy",
    )

    with pytest.raises(ValueError, match="one population and evidence scope"):
        evaluate_records((adult, child))


def test_evaluation_rejects_target_user_scope_for_proxy_population() -> None:
    record = _record(
        ("a",),
        ("a",),
        evidence_scope="target_user_validation",
    )

    with pytest.raises(ValueError, match="target_user_child"):
        evaluate_records((record,))


def test_evaluation_rejects_duplicate_utterance_ids() -> None:
    with pytest.raises(ValueError, match="utterance_id values must be unique"):
        evaluate_records(
            (
                _record(("a",), ("a",)),
                _record(("m",), ("m",)),
            )
        )


def test_evaluation_jsonl_cli_writes_aggregate_report_without_sequences(tmp_path) -> None:
    input_path = tmp_path / "evaluation.jsonl"
    output_path = tmp_path / "report.json"
    rows = [
        {
            "utterance_id": "utt-1",
            "reference": ["a", "m"],
            "predicted_tokens": ["a", "n"],
            "blank_token": "<blank>",
            "population": "adult_tamil_proxy",
            "evidence_scope": "engineering_proxy",
            "scorable": True,
        }
    ]
    input_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    assert main(["--input", str(input_path), "--output", str(output_path)]) == 0
    output = json.loads(output_path.read_text(encoding="utf-8"))

    assert output["micro_per"] == pytest.approx(0.5)
    assert "reference" not in output
    assert "predicted_tokens" not in output

