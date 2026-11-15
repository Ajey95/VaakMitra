"""DEC-046 / PHN-006: checkpoint metrics use the actual deployment decoder."""

import numpy as np
import pytest
import torch


def test_dec046_evaluation_respects_beam_without_changing_default_greedy(
    tmp_path, monkeypatch
):
    from scripts.model import finetune_mobile_phoneme as runner

    np.save(tmp_path / "audio.npy", np.zeros((1, 48000), dtype=np.float32))
    monkeypatch.setattr(runner, "OUT", tmp_path)
    meta = {"rows": [{"split": "calibration", "targets": [1], "is_target": True}]}

    class Ambiguous(torch.nn.Module):
        def forward(self, wave):
            # Greedy blank/blank loses the phone; summed CTC paths recover it.
            return torch.log(torch.tensor([[[0.6, 0.4], [0.6, 0.4]]])).expand(
                len(wave), -1, -1
            )

    model = Ambiguous()
    assert (
        runner.evaluate(model, meta, "calibration", "cpu")["all"]["phoneme_error_rate"]
        == 1
    )
    beam = {"type": "ctc_prefix_beam", "beam_width": 5, "nonblank_top_k": 1}
    assert (
        runner.evaluate(model, meta, "calibration", "cpu", decoder=beam)["all"][
            "phoneme_error_rate"
        ]
        == 0
    )
    assert (
        runner.evaluate(model, meta, "calibration", "cpu", decoder={"type": "greedy"})[
            "all"
        ]["phoneme_error_rate"]
        == 1
    )
    with pytest.raises(ValueError):
        runner.evaluate(model, meta, "calibration", "cpu", decoder={})
