"""PHN-006: interpretable edit totals without changing the frozen decoder."""

from scripts.model.phoneme_error_analysis import edit_counts


def test_phn006_edit_accounting_handles_repeats_and_empty_sequences():
    assert edit_counts(["a", "b", "c"], ["a", "x", "c", "d"]) == {
        "substitution": 1,
        "deletion": 0,
        "insertion": 1,
    }
    assert edit_counts(["a", "b", "b"], ["a", "b"]) == {
        "substitution": 0,
        "deletion": 1,
        "insertion": 0,
    }
    assert edit_counts(["a", "b"], []) == {
        "substitution": 0,
        "deletion": 2,
        "insertion": 0,
    }
