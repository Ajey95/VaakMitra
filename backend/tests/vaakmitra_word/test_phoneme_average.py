"""PHN-001/006: combine only aligned, same-source checkpoint parameters."""

import copy

import pytest
import torch

from scripts.model.average_phoneme_checkpoints import average_states


def state(value):
    return {
        "model": {
            "weight": torch.tensor([value], dtype=torch.float32),
            "bn.num_batches_tracked": torch.tensor(int(value)),
            "fixed": torch.tensor([1]),
        },
        "binding": {"source": "same"},
        "dataset_sha256": "rows",
        "encoder_blocks": 5,
        "frame_shift_ms": 40,
        "experiment_config": {"initial_checkpoint_sha256": "common"},
    }


def test_phn001_average_preserves_inputs_and_fixed_buffers():
    a, b = state(2), state(4)
    merged = average_states(a, b)
    assert merged["weight"].tolist() == [3]
    assert merged["bn.num_batches_tracked"].item() == 4
    assert a["model"]["weight"].tolist() == [2]
    merged["fixed"][0] = 9
    assert a["model"]["fixed"].tolist() == [1]


@pytest.mark.parametrize(
    "key,value",
    [("dataset_sha256", "different"), ("frame_shift_ms", 20), ("binding", {})],
)
def test_phn006_average_rejects_incompatible_sources_or_frame_contract(key, value):
    b = state(4)
    b[key] = value
    with pytest.raises(ValueError):
        average_states(state(2), b)


def test_phn006_average_requires_shared_initialization_and_tensor_shapes():
    a, b = state(2), state(4)
    b["experiment_config"]["initial_checkpoint_sha256"] = "other"
    with pytest.raises(ValueError):
        average_states(a, b)
    b = copy.deepcopy(a)
    b["model"]["weight"] = torch.zeros(2)
    with pytest.raises(ValueError):
        average_states(a, b)


def test_dec042_shared_source_training_loop_is_counted_once():
    from scripts.model.average_phoneme_checkpoints import unique_training_seconds

    config = {"output_root": "one-original-run", "seed": 401}
    reports = [{"seconds": 459.796}, {"seconds": 459.796}]
    assert unique_training_seconds([config, dict(config)], reports) == 459.796
    assert (
        unique_training_seconds(
            [config, {**config, "output_root": "different-original-run"}], reports
        )
        == 919.592
    )
    with pytest.raises(ValueError, match="source|duration"):
        unique_training_seconds([config, dict(config)], [reports[0], {"seconds": 1}])


def test_dec043_weighted_average_keeps_parents_and_exact_mixture():
    left, right = state(2), state(4)
    mixed = average_states(left, right, right_weight=0.8)
    assert mixed["weight"].item() == pytest.approx(3.6)
    assert mixed["bn.num_batches_tracked"].item() == 4
    assert left["model"]["weight"].item() == 2
    assert right["model"]["weight"].item() == 4


@pytest.mark.parametrize(
    "weight", [-0.1, 0.0, 1.0, 1.1, float("nan"), float("inf"), True]
)
def test_dec043_weighted_average_rejects_invalid_mixture(weight):
    with pytest.raises(ValueError, match="weight"):
        average_states(state(2), state(4), right_weight=weight)


@pytest.mark.parametrize("seconds", [float("nan"), float("inf"), -1])
def test_dec042_average_rejects_invalid_source_duration(seconds):
    from scripts.model.average_phoneme_checkpoints import unique_training_seconds

    with pytest.raises(ValueError):
        unique_training_seconds([{"output_root": "run"}], [{"seconds": seconds}])


@pytest.mark.parametrize("tamper", ["config", "source"])
def test_dec049_average_authenticates_parent_before_formation(
    tmp_path, monkeypatch, tamper
):
    import json
    import sys

    from scripts.model import average_phoneme_checkpoints as averaging
    from scripts.model.finetune_mobile_phoneme import sha

    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "dataset.json").write_text("{}", encoding="utf8")
    parents = []
    for name in ("left", "right"):
        p = tmp_path / name
        p.mkdir()
        source = p / "training-entrypoint.py"
        source.write_text("# actual source", encoding="utf8")
        cfg = {
            "input_root": str(inputs),
            "dataset_sha256": sha(inputs / "dataset.json"),
            "training_entrypoint_sha256": sha(source),
            "retained_target_train": 10,
        }
        torch.save({"experiment_config": cfg}, p / "best.pt")
        (p / "config.json").write_text(json.dumps(cfg), encoding="utf8")
        (p / "training-results.json").write_text(
            json.dumps(
                {
                    "checkpoint_sha256": sha(p / "best.pt"),
                    "evaluation_accessed": False,
                    "seconds": 1,
                }
            ),
            encoding="utf8",
        )
        parents.append(p)
    if tamper == "config":
        cfg = json.loads((parents[0] / "config.json").read_text())
        cfg["retained_target_train"] = 999
        (parents[0] / "config.json").write_text(json.dumps(cfg))
    else:
        (parents[0] / "training-entrypoint.py").write_text("# changed source")
    output = tmp_path / "must-not-be-created"
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "average",
            "--run",
            str(parents[0]),
            "--run",
            str(parents[1]),
            "--output-root",
            str(output),
        ],
    )
    with pytest.raises(ValueError, match="configuration|source"):
        averaging.main()
    assert not output.exists()
