"""DEC-030 / PHN-001,002,003,006: independent sampling and safe experiments."""

import numpy as np
import pytest
import torch

from scripts.model.improve_mobile_phoneme import (
    balanced_weights,
    create_run_directory,
    rate_in_padding,
    select_extra_quality_indices,
    select_training_indices,
    shift_in_padding,
    validate_initial_checkpoint,
)


def test_phn002_extra_quality_keeps_original_train_and_excludes_all_audit():
    rows = [
        {"split": "train"},
        {"split": "calibration"},
        {"split": "train", "quality_score": 0.94},
        {"split": "train", "quality_score": 0.98},
        {"split": "evaluation", "quality_score": 1},
    ]
    assert select_extra_quality_indices(rows, 2, 0.95) == [0, 3]
    with pytest.raises(ValueError):
        select_extra_quality_indices(rows, 2, 1.1)
    with pytest.raises(ValueError):
        select_extra_quality_indices(rows + [{"split": "train"}], 2, 0.95)


def test_phn003_rate_augmentation_never_crops_active_audio():
    short = torch.zeros(2, 48000)
    short[0, 20000:28000] = 0.2
    short[1] = 0.2
    slow = rate_in_padding(short, 1.1)
    assert slow.shape == short.shape
    assert torch.equal(slow[1], short[1])
    assert (slow[0].abs() > 0.1).sum() > 8000
    fast = rate_in_padding(short, 0.9)
    assert fast.shape == short.shape and torch.isfinite(fast).all()
    assert (fast[0].abs() > 0.1).sum() < 8000
    with pytest.raises(ValueError):
        rate_in_padding(short, 1.5)


def test_phn001_existing_output_checkpoint_cannot_be_overwritten(tmp_path):
    run = tmp_path / "baseline"
    run.mkdir()
    checkpoint = run / "best.pt"
    checkpoint.write_bytes(b"preserve original checkpoint")
    with pytest.raises(FileExistsError):
        create_run_directory(run)
    assert checkpoint.read_bytes() == b"preserve original checkpoint"
    fresh = tmp_path / "new-run"
    assert create_run_directory(fresh) == fresh.resolve()


def test_phn002_balances_words_without_heldout_sampling():
    rows = [{"split": "train", "is_target": True, "word_id": "a"}] * 2
    rows += [{"split": "train", "is_target": True, "word_id": "b"}]
    rows += [{"split": "train", "is_target": False, "word_id": None}] * 4
    weights = balanced_weights(rows, 0.5)
    assert np.isclose(weights[:2].sum(), 0.25)
    assert np.isclose(weights[2], 0.25)
    assert np.isclose(weights[3:].sum(), 0.5)
    with pytest.raises(ValueError, match="train"):
        balanced_weights(rows + [{"split": "evaluation"}], 0.5)
    with pytest.raises(ValueError):
        balanced_weights(rows, 1.1)


def test_phn003_jitter_preserves_all_samples_and_refuses_wrapping_content():
    audio = torch.zeros(2, 100)
    audio[0, 40:60] = torch.arange(20, dtype=torch.float32) + 1
    audio[1] = torch.arange(100, dtype=torch.float32) + 1
    shifted = shift_in_padding(audio, 12)
    assert torch.equal(shifted[0, 52:72], audio[0, 40:60])
    assert torch.equal(shifted[1], audio[1])
    assert torch.equal(shifted.square().sum(1), audio.square().sum(1))


def test_phn001_initial_checkpoint_rejects_wrong_source_or_architecture():
    meta = {"binding": {"base_sha256": "base", "vocabulary_sha256": "vocab"}}
    state = {"binding": meta["binding"], "encoder_blocks": 5, "dataset_sha256": "rows"}
    validate_initial_checkpoint(state, meta, "rows", 5)
    with pytest.raises(ValueError, match="dataset"):
        validate_initial_checkpoint(state, meta, "different", 5)
    with pytest.raises(ValueError, match="architecture"):
        validate_initial_checkpoint(state, meta, "rows", 7)
    with pytest.raises(ValueError, match="binding"):
        validate_initial_checkpoint({**state, "binding": {}}, meta, "rows", 5)


def test_phn002_quality_filter_never_includes_test_or_unknown_scores():
    rows = [
        {"split": "train", "audio_path": "a"},
        {"split": "train", "audio_path": "b"},
        {"split": "calibration", "audio_path": "c"},
    ]
    assert select_training_indices(rows, {"a": 0.95, "b": 0.7, "c": 1}, 0.9) == [0]
    with pytest.raises(ValueError, match="missing"):
        select_training_indices(rows, {"a": 0.95}, 0.9)


def test_phn001_expansion_requires_explicit_bound_parent_checkpoint():
    old = {"base_sha256": "base", "vocabulary_sha256": "vocab"}
    state = {"binding": old, "encoder_blocks": 5, "dataset_sha256": "oldrows"}
    meta = {
        "binding": dict(old, expansion_sha256="new"),
        "parent_binding": old,
        "parent_dataset_sha256": "oldrows",
    }
    with pytest.raises(ValueError):
        validate_initial_checkpoint(state, meta, "newrows", 5)
    validate_initial_checkpoint(state, meta, "newrows", 5, allow_expansion=True)
    with pytest.raises(ValueError, match="vocabulary"):
        validate_initial_checkpoint(
            state,
            dict(meta, binding=dict(meta["binding"], vocabulary_sha256="different")),
            "newrows",
            5,
            allow_expansion=True,
        )
    with pytest.raises(ValueError):
        validate_initial_checkpoint(
            state,
            dict(meta, parent_dataset_sha256="wrong"),
            "newrows",
            5,
            allow_expansion=True,
        )


def test_phn001_freeze_encoder_preserves_parameters_and_batchnorm_state():
    import torch

    from app.vaakmitra_word.phoneme_ctc import MobilePhonemeCtc
    from scripts.model.improve_mobile_phoneme import configure_encoder_training

    model = MobilePhonemeCtc(3, 5, frame_shift_ms=40)
    before = {k: v.clone() for k, v in model.encoder.state_dict().items()}
    model.train()
    configure_encoder_training(model, True)
    assert not model.encoder.training
    assert all(not p.requires_grad for p in model.encoder.parameters())
    loss = model(torch.randn(2, 48000)).square().mean()
    loss.backward()
    assert model.head.weight.grad is not None
    assert all(p.grad is None for p in model.encoder.parameters())
    assert all(torch.equal(before[k], v) for k, v in model.encoder.state_dict().items())
    configure_encoder_training(model, False)
    assert model.encoder.training and all(
        p.requires_grad for p in model.encoder.parameters()
    )


def test_phn001_training_dropout_preserves_eval_graph_and_weights():
    from app.vaakmitra_word.phoneme_ctc import MobilePhonemeCtc
    from scripts.model.improve_mobile_phoneme import configure_recurrent_dropout

    model = MobilePhonemeCtc(3, 5, frame_shift_ms=40).eval()
    x = torch.randn(2, 48000)
    before = {k: v.clone() for k, v in model.state_dict().items()}
    with torch.inference_mode():
        expected = model(x)
    configure_recurrent_dropout(model, 0.2)
    assert model.sequence.dropout == 0.2
    with torch.inference_mode():
        assert torch.equal(expected, model(x))
    assert all(torch.equal(before[k], v) for k, v in model.state_dict().items())
    for invalid in [-0.1, 0.6, float("nan")]:
        with pytest.raises(ValueError):
            configure_recurrent_dropout(model, invalid)


def test_dec044_blank_bias_changes_only_blank_logit_and_preserves_other_weights():
    from app.vaakmitra_word.phoneme_ctc import MobilePhonemeCtc
    from scripts.model.improve_mobile_phoneme import configure_blank_bias

    torch.set_num_threads(1)
    torch.manual_seed(44)
    model = MobilePhonemeCtc(3, 5).eval()
    wave = torch.linspace(-0.1, 0.1, 48000).unsqueeze(0)
    weights = {key: value.clone() for key, value in model.state_dict().items()}
    with torch.inference_mode():
        before = model(wave)
    configure_blank_bias(model, -0.2)
    with torch.inference_mode():
        after = model(wave)
    assert torch.equal(after[..., 1:], before[..., 1:])
    assert torch.allclose(after[..., 0], before[..., 0] - 0.2, atol=1e-7)
    for key, value in model.state_dict().items():
        if key == "head.bias":
            assert torch.equal(value[1:], weights[key][1:])
        else:
            assert torch.equal(value, weights[key])


@pytest.mark.parametrize(
    "offset", [float("nan"), float("inf"), -0.51, 0.51, True, "0.1"]
)
def test_dec044_blank_bias_rejects_invalid_scalar(offset):
    from app.vaakmitra_word.phoneme_ctc import MobilePhonemeCtc
    from scripts.model.improve_mobile_phoneme import configure_blank_bias

    with pytest.raises(ValueError, match="blank"):
        configure_blank_bias(MobilePhonemeCtc(3, 5), offset)


def test_dec046_first_qualified_checkpoint_replaces_better_unqualified_proxy():
    from scripts.model.improve_mobile_phoneme import deployment_checkpoint_decision

    def metrics(target, overall):
        return {
            "target19": {"phoneme_error_rate": target},
            "all": {"phoneme_error_rate": overall},
        }

    baseline, anchor = metrics(0.06, 0.55), metrics(0.07, 0.54)
    value, qualified, improved = deployment_checkpoint_decision(
        metrics(0.05, 0.549), 0.192, False, baseline, anchor
    )
    assert value > 0.192 and qualified and improved
    _, qualified, improved = deployment_checkpoint_decision(
        metrics(0.06, 0.45), value, True, baseline, anchor
    )
    assert not qualified and not improved
    with pytest.raises(ValueError, match="finite"):
        deployment_checkpoint_decision(
            metrics(float("nan"), 0.54), value, True, baseline, anchor
        )


def test_dec047_fixed_normalization_keeps_buffers_but_trains_encoder_and_head():
    from app.vaakmitra_word.phoneme_ctc import MobilePhonemeCtc
    from scripts.model.improve_mobile_phoneme import configure_encoder_training

    torch.set_num_threads(1)
    torch.manual_seed(47)
    model = MobilePhonemeCtc(3, 5)
    buffers = {key: value.clone() for key, value in model.encoder.named_buffers()}
    encoder = {key: value.clone() for key, value in model.encoder.named_parameters()}
    head = model.head.weight.detach().clone()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    for _ in range(2):
        model.train()
        configure_encoder_training(model, False, freeze_statistics=True)
        assert model.encoder.training and model.sequence.training
        assert all(
            not layer.training
            for layer in model.encoder.modules()
            if isinstance(layer, torch.nn.BatchNorm1d)
        )
        optimizer.zero_grad()
        model(torch.randn(2, 48000)).square().mean().backward()
        optimizer.step()
    assert all(
        torch.equal(value, buffers[key]) for key, value in model.encoder.named_buffers()
    )
    assert any(
        not torch.equal(value, encoder[key])
        for key, value in model.encoder.named_parameters()
    )
    assert not torch.equal(model.head.weight, head)


def test_dec049_qualified_checkpoint_retains_one_phone_broader_improvement():
    from scripts.model.improve_mobile_phoneme import deployment_checkpoint_decision

    def metrics(target, overall):
        return {
            "target19": {"phoneme_error_rate": target},
            "all": {"phoneme_error_rate": overall},
        }

    baseline = metrics(31 / 547, 0.5529686618867317)
    anchor = metrics(36 / 547, 0.5470071699025215)
    before = 0.7 * (30 / 547) + 0.3 * (6800 / 12413)
    value, qualified, improved = deployment_checkpoint_decision(
        metrics(30 / 547, 6799 / 12413), before, True, baseline, anchor
    )
    assert 0 < before - value < 0.0001
    assert qualified and improved
    # Existing unqualified fallback tolerance still controls stopping.
    _, qualified, improved = deployment_checkpoint_decision(
        metrics(31 / 547, 6799 / 12413),
        0.7 * (31 / 547) + 0.3 * (6800 / 12413),
        False,
        baseline,
        anchor,
    )
    assert not qualified and not improved
