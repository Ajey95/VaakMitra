"""Unit tests for parent weekly rollup."""
from datetime import datetime, timedelta

from app.routers.parent import weekly_rollup


NOW = datetime(2026, 6, 28, 12, 0, 0)


def _ev(accuracy, stars, days_ago):
    return {
        "accuracy": accuracy,
        "stars_earned": stars,
        "created_at": NOW - timedelta(days=days_ago),
    }


def test_empty():
    out = weekly_rollup([], NOW)
    assert out["sessions_this_week"] == 0
    assert out["stars_this_week"] == 0
    assert out["accuracy_delta"] == 0.0


def test_counts_only_this_week():
    evs = [
        _ev(80, 3, 1),   # this week
        _ev(60, 1, 5),   # this week
        _ev(90, 3, 10),  # previous week
    ]
    out = weekly_rollup(evs, NOW)
    assert out["sessions_this_week"] == 2
    assert out["stars_this_week"] == 4
    assert out["avg_accuracy_this_week"] == 70.0
    assert out["avg_accuracy_prev_week"] == 90.0
    assert out["accuracy_delta"] == -20.0


def test_active_days_dedup():
    evs = [_ev(80, 1, 1), _ev(70, 1, 1), _ev(60, 1, 3)]  # two sessions same day
    out = weekly_rollup(evs, NOW)
    assert out["active_days_this_week"] == 2


def test_ignores_older_than_two_weeks_for_prev():
    evs = [_ev(50, 1, 20)]  # 20 days ago -> neither window
    out = weekly_rollup(evs, NOW)
    assert out["sessions_this_week"] == 0
    assert out["avg_accuracy_prev_week"] == 0.0
