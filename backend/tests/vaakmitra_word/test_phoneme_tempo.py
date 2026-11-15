"""DEC-050/PHN001,003: vary speaking pace without pitch changes or truncation."""

import pytest
import torch


def tones():
    torch.set_num_threads(1)
    wave = torch.zeros(2, 48000)
    time = torch.arange(6400) / 16000
    wave[0, 20800:27200] = 0.2 * torch.sin(2 * torch.pi * 500 * time)
    wave[1, 20800:27200] = 0.2 * torch.sin(2 * torch.pi * 1000 * time)
    return wave


def test_dec050_tempo_identity_and_silence_do_not_invent_signal():
    from scripts.model.improve_mobile_phoneme import tempo_in_padding

    x = tones()
    assert torch.equal(tempo_in_padding(x, 1), x)
    assert torch.count_nonzero(tempo_in_padding(torch.zeros_like(x), 3)) == 0


@pytest.mark.parametrize("factor", [1.5, 2.0, 3.0])
def test_dec050_tempo_preserves_independent_pitches_and_increases_duration(factor):
    from scripts.model.improve_mobile_phoneme import tempo_in_padding

    x = tones()
    before = x.clone()
    out = tempo_in_padding(x, factor)
    assert out.shape == x.shape and out.dtype == x.dtype and out.device == x.device
    assert torch.equal(x, before) and torch.isfinite(out).all()
    for index, hz in enumerate([500, 1000]):
        spectrum = torch.fft.rfft(out[index])
        peak = int(spectrum.abs().argmax()) * 16000 / 48000
        assert abs(peak - hz) < 4
        active = int((out[index].abs() > 0.02).sum())
        original = int((x[index].abs() > 0.02).sum())
        assert factor * 0.8 < active / original < factor * 1.2


def test_dec050_tempo_never_discards_active_audio_or_mutates_unsafe_rows():
    from scripts.model.improve_mobile_phoneme import tempo_in_padding

    x = tones()
    x[0] = 0.2 * torch.sin(2 * torch.pi * 500 * torch.arange(48000) / 16000)
    out = tempo_in_padding(x, 2)
    assert torch.equal(out[0], x[0])
    assert not torch.equal(out[1], x[1])


@pytest.mark.parametrize(
    "factor", [0, -1, 0.5, 4, float("nan"), float("inf"), True, "2"]
)
def test_dec050_tempo_rejects_unsupported_factor(factor):
    from scripts.model.improve_mobile_phoneme import tempo_in_padding

    with pytest.raises(ValueError):
        tempo_in_padding(tones(), factor)
