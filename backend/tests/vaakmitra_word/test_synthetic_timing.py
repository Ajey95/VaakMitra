"""PHN012: controlled recording transforms retain declared time/pitch properties."""
import numpy as np
from app.vaakmitra_word.synthetic_timing import time_stretch, pitch_shift, robustness_variants


def tone():
    return (.2*np.sin(2*np.pi*440*np.arange(16000)/16000)).astype(np.float32)


def dominant(wave):
    spectrum=np.abs(np.fft.rfft(wave*np.hanning(len(wave))))
    return np.argmax(spectrum)*16000/len(wave)


def test_phn012_stretch_changes_duration_without_changing_tone_pitch():
    wave=tone();slow=time_stretch(wave,.75);fast=time_stretch(wave,1.3)
    assert len(slow)==round(len(wave)/.75)
    assert len(fast)==round(len(wave)/1.3)
    assert abs(dominant(slow)-440)<6
    assert abs(dominant(fast)-440)<6


def test_phn012_pitch_shift_keeps_duration_and_moves_pitch():
    shifted=pitch_shift(tone(),3)
    assert len(shifted)==16000
    assert abs(dominant(shifted)-440*2**.25)<8


def test_phn012_variants_are_deterministic_finite_and_keep_clean_parent():
    wave=tone();a=robustness_variants(wave,123);b=robustness_variants(wave,123)
    assert len(a)==10
    np.testing.assert_array_equal(a['clean'],wave)
    for key in a:
        np.testing.assert_array_equal(a[key],b[key])
        assert np.isfinite(a[key]).all() and np.max(np.abs(a[key]))<=.99
    assert len(a['uneven_pauses'])>len(wave)
    assert np.sqrt(np.mean(a['low_volume']**2))<np.sqrt(np.mean(wave**2))*.11


def test_phn012_clean_near_full_scale_parent_is_not_normalized():
    wave=tone()*4.995
    np.testing.assert_array_equal(robustness_variants(wave,123)['clean'],wave)


def test_phn012_short_supported_inputs_use_matching_fft_dimensions():
    wave=tone()[:800]
    assert len(time_stretch(wave[:400],.75))==533
    assert len(robustness_variants(wave,123))==10
