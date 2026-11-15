"""PHN-006: freeze a candidate using calibration evidence alone."""

import pytest

from scripts.model.select_phoneme_improvement import (
    select_candidate,
    validate_comparison_rows,
    validate_final_metrics,
    validate_selection_binding,
)


def test_phn006_expanded_selection_requires_identical_original_heldout_rows():
    base = [
        {"split": "train", "id": "a"},
        {"split": "calibration", "id": "b"},
        {"split": "evaluation", "id": "c"},
    ]
    validate_comparison_rows(base, base + [{"split": "train", "id": "d"}])
    with pytest.raises(ValueError):
        validate_comparison_rows(base, base + [{"split": "calibration", "id": "d"}])
    with pytest.raises(ValueError):
        validate_comparison_rows(
            base, [base[0], {"split": "calibration", "id": "new"}, base[2]]
        )


def test_phn006_selection_rejects_replacement_weights_or_dataset():
    result = {"checkpoint_sha256": "selected"}
    config = {"dataset_sha256": "rows"}
    validate_selection_binding(result, config, "selected", "rows")
    with pytest.raises(ValueError, match="checkpoint"):
        validate_selection_binding(result, config, "replacement", "rows")
    with pytest.raises(ValueError, match="dataset"):
        validate_selection_binding(result, config, "selected", "different")


def result(target, overall, accessed=False):
    return {
        "evaluation_accessed": accessed,
        "calibration": {
            "target19": {"phoneme_error_rate": target},
            "all": {"phoneme_error_rate": overall},
        },
    }


@pytest.mark.parametrize("slot", ["baseline", "candidate", "anchor"])
@pytest.mark.parametrize("metric", ["all", "target19"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), -0.01])
def test_dec040_final_gate_rejects_invalid_per(slot, metric, bad):
    values = {
        "baseline": result(0.15, 0.59)["calibration"],
        "candidate": result(0.14, 0.591)["calibration"],
        "anchor": result(0.16, 0.583)["calibration"],
    }
    values[slot][metric]["phoneme_error_rate"] = bad
    with pytest.raises(ValueError, match="finite|nonnegative"):
        validate_final_metrics(
            values["baseline"], values["candidate"], 0, values["anchor"]
        )


def test_dec040_per_above_one_is_valid_and_selection_checks_reference():
    validate_final_metrics(
        result(1.5, 1.2)["calibration"], result(1.4, 1.2)["calibration"], 0
    )
    with pytest.raises(ValueError, match="finite|nonnegative"):
        select_candidate(
            {"a": result(0.1, 0.5)}, result(0.2, float("nan"))["calibration"]
        )


def test_dec040_wrong_same_data_legacy_anchor_is_rejected(tmp_path):
    import json

    from scripts.model.finetune_mobile_phoneme import sha
    from scripts.model.select_phoneme_decoder import load_regression_anchor

    (tmp_path / "dataset.json").write_text("same prepared data")
    (tmp_path / "best.pt").write_bytes(b"wrong anchor checkpoint")
    (tmp_path / "training-results.json").write_text(
        json.dumps(
            {
                "checkpoint_sha256": sha(tmp_path / "best.pt"),
                "calibration": result(0.05, 0.56)["calibration"],
            }
        )
    )
    with pytest.raises(ValueError, match="fixed|identity|anchor"):
        load_regression_anchor(tmp_path, sha(tmp_path / "dataset.json"), 61)


def test_dec040_anchor_is_inherited_and_cannot_be_replaced(tmp_path):
    import json

    from scripts.model.select_phoneme_decoder import (
        FIXED_ANCHOR_CHECKPOINT,
        resolve_regression_anchor_root,
    )

    anchor = tmp_path / "recorded-anchor"
    (tmp_path / "selection.json").write_text(
        json.dumps(
            {
                "regression_anchor": {
                    "root": str(anchor),
                    "checkpoint_sha256": FIXED_ANCHOR_CHECKPOINT,
                }
            }
        )
    )
    assert resolve_regression_anchor_root(tmp_path, None) == anchor
    wrong = tmp_path / "wrong"
    wrong.mkdir()
    (wrong / "best.pt").write_bytes(b"different checkpoint")
    with pytest.raises(ValueError, match="anchor"):
        resolve_regression_anchor_root(tmp_path, wrong)
    assert resolve_regression_anchor_root(wrong, None) is None


def test_dec040_future_selection_binds_helper_and_rejects_tampering(tmp_path):
    from scripts.model.select_phoneme_improvement import (
        capture_selection_helper,
        validate_selection_helper,
    )

    selected = {}
    capture_selection_helper(tmp_path, selected)
    assert len(selected["selection_helper_sha256"]) == 64
    validate_selection_helper(tmp_path, selected)
    (tmp_path / "selection-helper.py").write_text("replaced ranking helper")
    with pytest.raises(ValueError, match="helper"):
        validate_selection_helper(tmp_path, selected)
    validate_selection_helper(tmp_path, {})  # Existing historical freezes remain valid.


def test_phn006_broader_anchor_prevents_round_by_round_regression():
    baseline = result(0.0585, 0.55039)["calibration"]
    anchor = result(0.0658, 0.547007)["calibration"]
    with pytest.raises(ValueError):
        select_candidate(
            {"ratcheted": result(0.05, 0.559)}, baseline, regression_anchor=anchor
        )
    assert (
        select_candidate(
            {"bounded": result(0.05, 0.556)}, baseline, regression_anchor=anchor
        )
        == "bounded"
    )


def test_phn006_final_anchor_prevents_round_by_round_regression():
    baseline_test = result(0.148148, 0.589723)["calibration"]
    anchor_test = result(0.161111, 0.582967)["calibration"]
    with pytest.raises(ValueError):
        validate_final_metrics(
            baseline_test,
            result(0.14, 0.596)["calibration"],
            0,
            regression_anchor=anchor_test,
        )
    validate_final_metrics(
        baseline_test,
        result(0.14, 0.592)["calibration"],
        0,
        regression_anchor=anchor_test,
    )


def test_phn006_regression_anchor_rejects_different_data(tmp_path):
    from scripts.model.select_phoneme_decoder import load_regression_anchor

    (tmp_path / "dataset.json").write_text("different dataset")
    with pytest.raises(ValueError):
        load_regression_anchor(tmp_path, "expected dataset digest", 61)


def test_phn006_rejects_worse_models_and_exposed_experiments():
    baseline = result(0.172, 0.578)["calibration"]
    winner = select_candidate(
        {"a": result(0.16, 0.56), "b": result(0.11, 0.56), "c": result(0.10, 0.9)},
        baseline,
    )
    assert winner == "b"
    with pytest.raises(ValueError):
        select_candidate({"a": result(0.16, 0.56, True)}, baseline)
    with pytest.raises(ValueError):
        select_candidate({"a": result(0.18, 0.55)}, baseline)


def test_phn006_deployment_requires_measured_test_improvement_and_export_parity():
    baseline = result(0.28333, 0.6115)["calibration"]
    candidate = result(0.22, 0.60)["calibration"]
    validate_final_metrics(baseline, candidate, 0)
    with pytest.raises(ValueError):
        validate_final_metrics(baseline, baseline, 0)
    with pytest.raises(ValueError):
        validate_final_metrics(baseline, candidate, 1)


def test_phn006_joint_comparison_uses_report_declared_decoder():
    from scripts.model.select_phoneme_decoder import validate_report_calibration

    greedy = result(0.07, 0.55)["calibration"]
    beam = result(0.065, 0.547)["calibration"]
    report = {
        "decoder": {"type": "ctc_prefix_beam", "beam_width": 5, "nonblank_top_k": 8},
        "calibration": beam,
    }
    validate_report_calibration(report, {"greedy": greedy, "ctc_prefix_beam": beam})
    validate_report_calibration(
        {"calibration": greedy}, {"greedy": greedy, "ctc_prefix_beam": beam}
    )
    with pytest.raises(ValueError):
        validate_report_calibration(
            report, {"greedy": greedy, "ctc_prefix_beam": greedy}
        )
    with pytest.raises(ValueError):
        validate_report_calibration(
            {**report, "decoder": None}, {"greedy": greedy, "ctc_prefix_beam": beam}
        )


def test_phn006_baseline_packaging_resolves_bound_original_training_source(tmp_path):
    import hashlib
    import json

    import torch

    from scripts.model.select_phoneme_decoder import resolve_training_provenance

    run = tmp_path / "old-run"
    run.mkdir()
    source = run / "training-entrypoint.py"
    source.write_text("training source")
    baseline = tmp_path / "selected"
    baseline.mkdir()
    config = {
        "training_entrypoint_sha256": hashlib.sha256(source.read_bytes()).hexdigest()
    }
    (baseline / "active-training-config.json").write_text(json.dumps(config))
    torch.save({"experiment_config": config}, baseline / "best.pt")
    (baseline / "selection.json").write_text(json.dumps({"winner_run": str(run)}))
    cfg, src = resolve_training_provenance(baseline)
    assert cfg.name == "active-training-config.json" and src == source
    source.write_text("changed source")
    with pytest.raises(ValueError):
        resolve_training_provenance(baseline)


def test_phn006_provenance_rejects_replaced_same_source_configuration(tmp_path):
    import hashlib
    import json

    import torch

    from scripts.model.select_phoneme_decoder import resolve_training_provenance

    source = tmp_path / "training-entrypoint.py"
    source.write_text("same training source")
    config = {
        "training_entrypoint_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "seed": 211,
        "freeze_encoder": False,
    }
    torch.save({"experiment_config": config}, tmp_path / "best.pt")
    (tmp_path / "config.json").write_text(json.dumps({**config, "seed": 999}))
    with pytest.raises(ValueError):
        resolve_training_provenance(tmp_path)


def test_phn006_deployed_baseline_rejects_raw_greedy_report_substitution(tmp_path):
    import json

    from scripts.model.finetune_mobile_phoneme import BACKEND, sha
    from scripts.model.select_phoneme_decoder import load_baseline_report

    (tmp_path / "best.pt").write_bytes(b"checkpoint")
    checkpoint = sha(tmp_path / "best.pt")
    greedy = {
        "calibration": result(0.0676, 0.5515)["calibration"],
        "checkpoint_sha256": checkpoint,
    }
    beam = {
        **greedy,
        "decoder": {"type": "ctc_prefix_beam", "beam_width": 5, "nonblank_top_k": 8},
        "calibration": result(0.0658, 0.547)["calibration"],
    }
    selection = {
        "decoder": beam["decoder"],
        "checkpoint_sha256": checkpoint,
        "winner": "chosen",
        "experiments": {"chosen": beam},
        "evaluation_accessed": False,
        "selection_split": "calibration",
        "decoder_source_sha256": sha(BACKEND / "app/vaakmitra_word/phoneme_decoder.py"),
    }
    (tmp_path / "selection.json").write_text(json.dumps(selection))
    (tmp_path / "selection-freeze.json").write_text(
        json.dumps(
            {
                "selection_sha256": sha(tmp_path / "selection.json"),
                "checkpoint_sha256": checkpoint,
            }
        )
    )
    (tmp_path / "training-results.json").write_text(json.dumps(beam))
    assert load_baseline_report(tmp_path, 61) == beam
    (tmp_path / "training-results.json").write_text(json.dumps(greedy))
    with pytest.raises(ValueError):
        load_baseline_report(tmp_path, 61)
    (tmp_path / "selection.json").unlink()
    (tmp_path / "selection-freeze.json").unlink()
    assert load_baseline_report(tmp_path, 61) == greedy
