"""Unit tests for badge unlock logic."""
from app.routers.gamification import BADGES, evaluate_badges


def _by_id(badges):
    return {b["id"]: b for b in badges}


def test_new_user_unlocks_nothing():
    badges = evaluate_badges(0, 0, 0, 0)
    assert all(not b["unlocked"] for b in badges)
    assert len(badges) == len(BADGES)


def test_star_thresholds():
    badges = _by_id(evaluate_badges(total_stars=12, total_sessions=0,
                                    completed_lessons=0, high_accuracy_count=0))
    assert badges["first_words"]["unlocked"]      # >=1
    assert badges["rising_star"]["unlocked"]      # >=5
    assert badges["on_fire"]["unlocked"]          # >=10
    assert not badges["mic_master"]["unlocked"]   # >=20


def test_session_and_lesson_badges():
    badges = _by_id(evaluate_badges(0, total_sessions=10,
                                    completed_lessons=3, high_accuracy_count=0))
    assert badges["first_session"]["unlocked"]
    assert badges["dedicated"]["unlocked"]
    assert not badges["committed"]["unlocked"]    # needs 25
    assert badges["explorer"]["unlocked"]         # 3 lessons
    assert not badges["graduate"]["unlocked"]     # needs 6


def test_high_accuracy_badges():
    badges = _by_id(evaluate_badges(0, 0, 0, high_accuracy_count=5))
    assert badges["perfectionist"]["unlocked"]
    assert badges["sharp_shooter"]["unlocked"]


def test_progress_is_fractional_and_capped():
    badges = _by_id(evaluate_badges(total_stars=3, total_sessions=0,
                                    completed_lessons=0, high_accuracy_count=0))
    # rising_star needs 5 -> 3/5 = 0.6
    assert badges["rising_star"]["progress"] == 0.6
    # first_words needs 1, have 3 -> capped at 1.0
    assert badges["first_words"]["progress"] == 1.0
