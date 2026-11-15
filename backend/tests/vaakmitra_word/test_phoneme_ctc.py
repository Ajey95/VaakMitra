import numpy as np
import pytest
import torch
from app.vaakmitra_word.mobile_student_model import MobileWordStudent
from app.vaakmitra_word.phoneme_ctc import (
    MobilePhonemeCtc,
    checkpoint_frame_shift,
    choose_quantization,
    ctc_decode,
    prepare_waveform,
    stress_waveform,
    validate_splits,
)


def test_phn003_finer_frames_reuse_all_existing_weights():
    original = MobilePhonemeCtc(61, 5)
    dense = MobilePhonemeCtc(61, 5, frame_shift_ms=20)
    dense.load_state_dict(original.state_dict(), strict=True)
    assert torch.equal(
        dense.encoder[4].layers[3].weight, original.encoder[4].layers[3].weight
    )
    dense.eval()
    with torch.no_grad():
        assert dense(torch.zeros(1, 48000)).shape == (1, 150, 61)
    assert checkpoint_frame_shift({}) == 40
    assert checkpoint_frame_shift({"frame_shift_ms": 20}) == 20
    with pytest.raises(ValueError, match="frame"):
        checkpoint_frame_shift({"frame_shift_ms": 30})
    with pytest.raises(ValueError, match="frame"):
        MobilePhonemeCtc(61, 5, frame_shift_ms=30)


def test_encoder_transfer_and_temporal_resolution():
    base = MobileWordStudent()
    model = MobilePhonemeCtc(7)
    model.load_encoder(base.state_dict())
    assert torch.equal(model.encoder[0].weight, base.encoder[0].weight)
    model.eval()
    with torch.no_grad():
        output = model(torch.zeros(2, 48000))
    assert output.shape == (2, 75, 7)
    assert torch.isfinite(output).all()


def test_early_encoder_transfer_retains_phone_resolution():
    base = MobileWordStudent()
    model = MobilePhonemeCtc(7, encoder_blocks=5)
    model.load_encoder(base.state_dict())
    assert torch.equal(
        model.encoder[4].layers[3].weight, base.encoder[4].layers[3].weight
    )
    model.eval()
    with torch.no_grad():
        assert model(torch.zeros(1, 48000)).shape == (1, 75, 7)


def test_ctc_keeps_repeats_separated_by_blank():
    assert ctc_decode([0, 1, 1, 0, 1, 2, 2, 0]) == [1, 1, 2]


def test_waveform_keeps_duration_and_rejects_cropping():
    x = np.ones(5000, dtype=np.float32) * 0.1
    y = prepare_waveform(x)
    assert len(y) == 48000
    assert np.count_nonzero(y) == 5000
    with pytest.raises(ValueError):
        prepare_waveform(np.zeros(48001))


def test_split_guards_speakers_and_audio_duplicates():
    rows = [
        {"split": "train", "speaker": "a", "audio_sha256": "x"},
        {"split": "evaluation", "speaker": "b", "audio_sha256": "x"},
    ]
    with pytest.raises(ValueError, match="audio"):
        validate_splits(rows)
    rows[1]["audio_sha256"] = "y"
    rows[1]["speaker"] = "a"
    with pytest.raises(ValueError, match="speaker"):
        validate_splits(rows)


def test_stress_is_reproducible_and_duration_preserving():
    x = np.sin(np.arange(8000) * 0.1).astype(np.float32) * 0.2
    for kind in ("noise20", "noise10", "echo", "lowpass", "quiet"):
        y = stress_waveform(x, kind, 123)
        assert y.shape == x.shape
        assert np.isfinite(y).all()
        np.testing.assert_array_equal(y, stress_waveform(x, kind, 123))


def test_quantization_requires_calibration_quality_and_token_agreement():
    assert choose_quantization(0.2, 0.205, 0.99, 0.1, 0.105, 0.99) == "int8"
    assert choose_quantization(0.2, 0.25, 0.99, 0.1, 0.1, 1) == "fp32"
    assert choose_quantization(0.2, 0.2, 0.90, 0.1, 0.1, 1) == "fp32"
    assert choose_quantization(0.2, 0.2, 0.99, 0.1, 0.3, 0.99) == "fp32"
    assert choose_quantization(0.2, 0.2, 0.99, 0.1, 0.1, 0.8) == "fp32"
