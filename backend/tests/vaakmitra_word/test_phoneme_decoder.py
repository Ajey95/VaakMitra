"""PHN-001/003/006: target-free CTC sequence marginalization and bound metadata."""

import hashlib
import itertools
import json
from collections import defaultdict

import numpy as np
import pytest

from app.vaakmitra_word.phoneme_ctc import ctc_decode
from app.vaakmitra_word.phoneme_decoder import decode_logits, validate_decoder


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "selection_missing",
        "decoder_missing",
        "width_changed",
        "greedy_substitution",
        "freeze_changed",
    ],
)
def test_phn006_joint_export_cannot_silently_change_frozen_decoder(tmp_path, mutation):
    from scripts.model.finetune_mobile_phoneme import frozen_decoder, sha

    (tmp_path / "best.pt").write_bytes(b"checkpoint")
    cfg = {"type": "ctc_prefix_beam", "beam_width": 5, "nonblank_top_k": 8}
    report = {
        "decoder": cfg,
        "checkpoint_sha256": sha(tmp_path / "best.pt"),
        "calibration": {"valid": "calibration"},
    }
    (tmp_path / "training-results.json").write_text(json.dumps(report))
    import app.vaakmitra_word.phoneme_decoder as decoder_module

    source_sha = sha(decoder_module.__file__)
    selection = {
        "decoder": dict(cfg),
        "checkpoint_sha256": report["checkpoint_sha256"],
        "winner": "chosen",
        "experiments": {"chosen": report},
        "evaluation_accessed": False,
        "selection_split": "calibration",
        "decoder_source_sha256": source_sha,
    }
    frozen_bytes = json.dumps(selection).encode()
    (tmp_path / "selection-freeze.json").write_text(
        json.dumps(
            {
                "selection_sha256": hashlib.sha256(frozen_bytes).hexdigest(),
                "checkpoint_sha256": report["checkpoint_sha256"],
            }
        )
    )
    if mutation == "selection_missing":
        with pytest.raises(ValueError):
            frozen_decoder(tmp_path, 61)
        return
    if mutation == "decoder_missing":
        selection.pop("decoder")
    if mutation == "width_changed":
        selection["decoder"]["beam_width"] = 6
    if mutation == "greedy_substitution":
        selection["decoder"] = {"type": "greedy"}
    if mutation == "freeze_changed":
        selection["unused_extra"] = "altered after freeze"
    (tmp_path / "selection.json").write_text(json.dumps(selection))
    if mutation is None:
        assert frozen_decoder(tmp_path, 61) == cfg
        return
    with pytest.raises(ValueError):
        frozen_decoder(tmp_path, 61)


def test_phn003_beam_sums_paths_instead_of_forcing_a_word():
    x = np.log(np.array([[0.55, 0.45], [0.55, 0.45]]))
    assert decode_logits(x) == []
    assert decode_logits(
        x, {"type": "ctc_prefix_beam", "beam_width": 5, "nonblank_top_k": 1}
    ) == [1]


def test_phn003_beam_agrees_with_exact_small_path_enumeration():
    rng = np.random.default_rng(7)
    for _ in range(20):
        p = rng.dirichlet(np.ones(3), size=3)
        totals = defaultdict(float)
        for path in itertools.product(range(3), repeat=3):
            totals[tuple(ctc_decode(path))] += np.prod(
                [p[i, c] for i, c in enumerate(path)]
            )
        expected = min(totals, key=lambda seq: (-totals[seq], seq))
        # Ten beams retain every possible nonzero prefix for three frames/two phones.
        assert decode_logits(
            np.log(p),
            {"type": "ctc_prefix_beam", "beam_width": 10, "nonblank_top_k": 2},
        ) == list(expected)


def test_phn003_decoder_preserves_blank_separated_repeats_and_rejects_nan():
    x = np.array([[-9, 9], [9, -9], [-9, 9]], dtype=float)
    cfg = {"type": "ctc_prefix_beam", "beam_width": 5, "nonblank_top_k": 1}
    assert decode_logits(x, cfg) == [1, 1]
    assert decode_logits(np.zeros((0, 2)), cfg) == []
    with pytest.raises(ValueError):
        decode_logits(np.array([[0, np.nan]]), cfg)


@pytest.mark.parametrize(
    "cfg",
    [
        None,
        {},
        {"type": "unknown"},
        {"type": "greedy", "beam_width": 5},
        {"type": "ctc_prefix_beam", "beam_width": 5.5, "nonblank_top_k": 8},
        {"type": "ctc_prefix_beam", "beam_width": True, "nonblank_top_k": 8},
        {"type": "ctc_prefix_beam", "beam_width": 11, "nonblank_top_k": 8},
        {"type": "ctc_prefix_beam", "beam_width": 5, "nonblank_top_k": 61},
    ],
)
def test_phn006_present_decoder_config_is_strict(cfg):
    with pytest.raises(ValueError):
        validate_decoder(cfg, 61)


def test_phn006_export_requires_frozen_bound_decoder(tmp_path):
    import json

    from scripts.model.finetune_mobile_phoneme import frozen_decoder

    (tmp_path / "best.pt").write_bytes(b"checkpoint")
    assert frozen_decoder(tmp_path, 61) == {"type": "greedy"}
    (tmp_path / "selection.json").write_text(json.dumps({"decoder": None}))
    with pytest.raises(ValueError):
        frozen_decoder(tmp_path, 61)
    (tmp_path / "selection.json").write_text(
        json.dumps(
            {
                "decoder": {
                    "type": "ctc_prefix_beam",
                    "beam_width": 5,
                    "nonblank_top_k": 8,
                },
                "checkpoint_sha256": "wrong",
            }
        )
    )
    with pytest.raises(ValueError):
        frozen_decoder(tmp_path, 61)
    from scripts.model.finetune_mobile_phoneme import sha

    (tmp_path / "selection.json").write_text(
        json.dumps(
            {
                "decoder": {
                    "type": "ctc_prefix_beam",
                    "beam_width": 5,
                    "nonblank_top_k": 8,
                },
                "checkpoint_sha256": sha(tmp_path / "best.pt"),
                "decoder_source_sha256": "wrong",
                "evaluation_accessed": False,
                "selection_split": "calibration",
            }
        )
    )
    with pytest.raises(ValueError):
        frozen_decoder(tmp_path, 61)


def test_phn006_selector_loads_trained_weights_and_checks_binding(tmp_path):
    import torch

    from app.vaakmitra_word.phoneme_ctc import MobilePhonemeCtc
    from scripts.model.select_phoneme_decoder import load_selected_model

    model = MobilePhonemeCtc(3, 5, frame_shift_ms=40)
    with torch.no_grad():
        model.head.weight.zero_()
        model.head.bias.copy_(torch.tensor([0.0, 9.0, 0.0]))
    state = {
        "model": model.state_dict(),
        "binding": {"frozen": "data"},
        "dataset_sha256": "digest",
        "encoder_blocks": 5,
        "frame_shift_ms": 40,
    }
    path = tmp_path / "best.pt"
    torch.save(state, path)
    loaded = load_selected_model(
        path, {"binding": {"frozen": "data"}}, "digest", 3, "cpu"
    )
    assert not loaded.training
    with torch.inference_mode():
        assert loaded(torch.zeros(1, 48000)).argmax(-1).unique().tolist() == [1]
    with pytest.raises(ValueError):
        load_selected_model(
            path, {"binding": {"frozen": "different"}}, "digest", 3, "cpu"
        )
