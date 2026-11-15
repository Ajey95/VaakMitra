"""Unit tests for evaluation analytics summarization."""
from datetime import datetime

from app.routers.analysis import summarize_evaluations


def _ev(accuracy, gop, mfcc, airflow, phoneme, day):
    return {
        "accuracy": accuracy, "gop_score": gop, "mfcc_score": mfcc,
        "airflow_score": airflow, "phoneme": phoneme,
        "created_at": datetime(2026, 6, day),
    }


def test_empty_returns_no_data():
    out = summarize_evaluations([])
    assert out["has_data"] is False
    assert out["total_attempts"] == 0
    assert out["by_phoneme"] == []


def test_basic_aggregates():
    evs = [  # newest-first
        _ev(80, 0.8 * 100, 70, 0.5, "amma", 3),
        _ev(60, 0.6 * 100, 50, 0.3, "amma", 2),
        _ev(90, 0.9 * 100, 80, 0.9, "appa", 1),
    ]
    out = summarize_evaluations(evs)
    assert out["has_data"] is True
    assert out["total_attempts"] == 3
    assert out["best_accuracy"] == 90
    assert out["overall"] == round((80 + 60 + 90) / 3, 1)
    # airflow scaled to 0-100
    assert out["metrics"]["airflow"] == round((50 + 30 + 90) / 3, 1)


def test_per_phoneme_grouping_and_sort():
    evs = [
        _ev(50, 50, 50, 0.5, "amma", 2),
        _ev(70, 70, 70, 0.5, "amma", 1),
        _ev(95, 95, 95, 0.5, "appa", 3),
    ]
    out = summarize_evaluations(evs)
    phonemes = {p["phoneme"]: p for p in out["by_phoneme"]}
    assert phonemes["amma"]["attempts"] == 2
    assert phonemes["amma"]["accuracy"] == 60.0
    # sorted best-first
    assert out["by_phoneme"][0]["phoneme"] == "appa"
    # weakest is amma
    assert out["weakest"]["phoneme"] == "amma"


def test_history_is_oldest_first_with_labels():
    evs = [_ev(80, 80, 80, 0.5, "amma", 3), _ev(60, 60, 60, 0.5, "amma", 1)]
    out = summarize_evaluations(evs)
    assert [h["accuracy"] for h in out["history"]] == [60, 80]
    assert out["history"][0]["label"] == "06/01"
