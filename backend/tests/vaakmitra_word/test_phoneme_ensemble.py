"""DEC-048 / PHN-001,003,006: bounded audio-only posterior combination."""

import copy
import hashlib
from pathlib import Path

import numpy as np
import pytest
import torch


def ensemble_state():
    import app.vaakmitra_word.phoneme_ctc as architecture

    model = architecture.MobilePhonemeEnsemble(3)
    return {
        "model_kind": "posterior_mean_2",
        "ensemble_members": 2,
        "ensemble_weights": [0.5, 0.5],
        "encoder_blocks": 5,
        "frame_shift_ms": 40,
        "architecture_source_sha256": hashlib.sha256(
            Path(architecture.__file__).read_bytes()
        ).hexdigest(),
        "model": model.state_dict(),
    }


def test_dec048_ensemble_is_arithmetic_probability_mean_and_exports(tmp_path):
    import onnxruntime as ort

    from app.vaakmitra_word.phoneme_ctc import MobilePhonemeEnsemble

    torch.set_num_threads(1)
    model = MobilePhonemeEnsemble(3).eval()
    with torch.no_grad():
        for member, probabilities in zip(
            model.members, ([0.6, 0.3, 0.1], [0.1, 0.1, 0.8]), strict=True
        ):
            for parameter in member.parameters():
                parameter.zero_()
            member.head.bias.copy_(torch.tensor(probabilities).log())
    wave = torch.randn(1, 48000)
    with torch.inference_mode():
        result = model(wave)
    expected = torch.tensor([0.35, 0.2, 0.45]).expand(1, 75, 3)
    assert torch.allclose(result.exp(), expected, atol=1e-6)
    assert sum(p.numel() for p in model.parameters()) == sum(
        p.numel() for member in model.members for p in member.parameters()
    )
    output = tmp_path / "ensemble.onnx"
    torch.onnx.export(
        model,
        wave,
        str(output),
        input_names=["waveform"],
        output_names=["logits"],
        opset_version=17,
        dynamic_axes={"waveform": {0: "batch"}, "logits": {0: "batch"}},
        dynamo=False,
    )
    actual = ort.InferenceSession(str(output), providers=["CPUExecutionProvider"]).run(
        None, {"waveform": wave.numpy()}
    )[0]
    assert np.allclose(actual, result.numpy(), atol=1e-5)


def test_dec048_factory_preserves_single_legacy_and_reconstructs_ensemble():
    from app.vaakmitra_word.phoneme_ctc import MobilePhonemeCtc, model_from_checkpoint

    torch.set_num_threads(1)
    single = MobilePhonemeCtc(3, 5).eval()
    restored = model_from_checkpoint(
        {"encoder_blocks": 5, "model": single.state_dict()}, 3
    )
    wave = torch.randn(1, 48000)
    with torch.inference_mode():
        assert torch.equal(single(wave), restored(wave))
    state = ensemble_state()
    ensemble = model_from_checkpoint(state, 3)
    assert len(ensemble.members) == 2
    assert all(
        torch.equal(ensemble.state_dict()[k], value)
        for k, value in state["model"].items()
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("model_kind", "unknown"),
        ("ensemble_members", True),
        ("ensemble_members", 2.0),
        ("ensemble_members", 3),
        ("ensemble_weights", [0.2, 0.8]),
        ("architecture_source_sha256", "changed"),
        ("encoder_blocks", 7),
        ("frame_shift_ms", 20),
    ],
)
def test_dec048_ensemble_factory_rejects_unsupported_contract(key, value):
    from app.vaakmitra_word.phoneme_ctc import model_from_checkpoint

    state = ensemble_state()
    state[key] = value
    with pytest.raises(ValueError):
        model_from_checkpoint(state, 3)


@pytest.mark.parametrize("mutation", ["data", "binding", "frame", "kind", "blocks"])
def test_dec048_parent_contract_rejects_mixed_or_nested_models(mutation):
    from scripts.model.assemble_phoneme_ensemble import validate_parent_states

    state = {
        "model_kind": "single",
        "binding": {"vocabulary_sha256": "vocab"},
        "dataset_sha256": "data",
        "encoder_blocks": 5,
        "frame_shift_ms": 40,
    }
    a, b = copy.deepcopy(state), copy.deepcopy(state)
    validate_parent_states([a, b], "data", state["binding"])
    if mutation == "data":
        b["dataset_sha256"] = "different"
    elif mutation == "binding":
        b["binding"] = {}
    elif mutation == "frame":
        b["frame_shift_ms"] = 20
    elif mutation == "kind":
        b["model_kind"] = "posterior_mean_2"
    else:
        b["encoder_blocks"] = 7
    with pytest.raises(ValueError):
        validate_parent_states([a, b], "data", state["binding"])


def test_dec048_single_trainer_rejects_ensemble_continuation_explicitly():
    from scripts.model.improve_mobile_phoneme import validate_initial_checkpoint

    with pytest.raises(ValueError, match="single"):
        validate_initial_checkpoint({"model_kind": "posterior_mean_2"}, {}, "data", 5)


@pytest.mark.parametrize("witnessed", [False, True])
def test_dec049_actual_loader_rejects_encoder_dependency_drift(
    tmp_path, monkeypatch, witnessed
):
    import json

    import app.vaakmitra_word.mobile_student_model as encoder
    from scripts.model.finetune_mobile_phoneme import sha
    from scripts.model.select_phoneme_decoder import load_selected_model

    state = ensemble_state()
    state.update(binding={"same": True}, dataset_sha256="data")
    expected = sha(Path(encoder.__file__))
    if not witnessed:
        state["encoder_architecture_source_sha256"] = expected
    checkpoint = tmp_path / "best.pt"
    torch.save(state, checkpoint)
    if witnessed:
        (tmp_path / "pre-evaluation-freeze.json").write_text(
            json.dumps(
                {
                    "checkpoint_sha256": sha(checkpoint),
                    "architecture_source_sha256": state["architecture_source_sha256"],
                    "encoder_architecture_source_sha256": expected,
                }
            ),
            encoding="utf8",
        )
    changed = tmp_path / "encoder.py"
    changed.write_text("# shape-compatible behavior change", encoding="utf8")
    monkeypatch.setattr(encoder, "__file__", str(changed))
    with pytest.raises(ValueError, match="encoder.*dependency"):
        load_selected_model(checkpoint, {"binding": state["binding"]}, "data", 3, "cpu")
