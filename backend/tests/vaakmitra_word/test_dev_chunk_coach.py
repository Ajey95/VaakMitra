"""DEC-023/DCH-001..002: written-chunk hints never diagnose speech sounds."""

from app.vaakmitra_word.dev_chunk_coach import build_chunk_coach


def test_dch001_amma_chunks_reconstruct_and_first_text_difference_is_start():
    hint = build_chunk_coach("அம்மா", "அப்பா", capture_valid=True)
    assert hint == {
        "status": "text_hypothesis",
        "target_word": "அம்மா",
        "chunks": ["அம்", "மா"],
        "focus_index": 0,
        "focus_position": "start",
        "basis": "unvalidated_asr_text_difference",
    }


def test_dch002_ending_difference_selects_last_written_chunk():
    hint = build_chunk_coach("அம்மா", "அம்மி", capture_valid=True)
    assert hint["chunks"] == ["அம்", "மா"]
    assert hint["focus_index"] == 1
    assert hint["focus_position"] == "end"


def test_dch002_missing_identical_cross_script_and_invalid_capture_do_not_localize():
    for candidate, valid in ((None, True), ("அம்மா", True), ("amma", True), ("அப்பா", False)):
        hint = build_chunk_coach("அம்மா", candidate, capture_valid=valid)
        assert hint["status"] == "visual_only"
        assert hint["focus_index"] is None
        assert hint["focus_position"] is None
        assert hint["basis"] == "manual_visual_practice"
        assert "candidate" not in hint


def test_dch001_long_word_has_at_most_three_nonempty_exact_chunks():
    target = "கழிப்பறை"
    hint = build_chunk_coach(target, None, capture_valid=True)
    assert 1 <= len(hint["chunks"]) <= 3
    assert all(hint["chunks"])
    assert "".join(hint["chunks"]) == target
