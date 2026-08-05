from __future__ import annotations

import json
from pathlib import Path

from modeling.teacher.preflight import TeacherEnvironmentProbe, evaluate_teacher_preflight
from modeling.teacher.run_preflight import main

CONFIG_PATH = Path("modeling/configs/indicconformer_teacher.json")


def _probe(**overrides: object) -> TeacherEnvironmentProbe:
    payload: dict[str, object] = {
        "model_id": "ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large",
        "model_revision": "a" * 40,
        "access_authorized": True,
        "nemo_available": True,
        "torch_available": True,
        "cuda_available": True,
        "cuda_device_count": 1,
        "free_storage_bytes": 100_000_000_000,
    }
    payload.update(overrides)
    return TeacherEnvironmentProbe.model_validate(payload)


def test_full_training_preflight_refuses_missing_gated_access_first() -> None:
    report = evaluate_teacher_preflight(
        _probe(access_authorized=False, cuda_available=False, cuda_device_count=0),
        mode="full_train",
    )

    assert report.ready is False
    assert report.code == "model_access_not_authorized"
    assert "token" not in json.dumps(report.model_dump(mode="json")).casefold()


def test_full_training_preflight_refuses_cpu_only_host() -> None:
    report = evaluate_teacher_preflight(
        _probe(cuda_available=False, cuda_device_count=0), mode="full_train"
    )

    assert report.ready is False
    assert report.code == "gpu_required_for_full_training"


def test_cpu_smoke_is_ready_without_gated_model_or_cuda() -> None:
    report = evaluate_teacher_preflight(
        _probe(
            access_authorized=False,
            nemo_available=False,
            cuda_available=False,
            cuda_device_count=0,
        ),
        mode="cpu_smoke",
    )

    assert report.ready is True
    assert report.code == "cpu_smoke_ready"
    assert report.evidence_scope == "fixture_encoder_shapes_only"


def test_feature_extraction_requires_model_access_and_nemo_but_not_cuda() -> None:
    missing_nemo = evaluate_teacher_preflight(
        _probe(nemo_available=False, cuda_available=False, cuda_device_count=0),
        mode="feature_extract",
    )
    cpu_ready = evaluate_teacher_preflight(
        _probe(cuda_available=False, cuda_device_count=0), mode="feature_extract"
    )

    assert missing_nemo.code == "nemo_dependency_missing"
    assert cpu_ready.ready is True
    assert cpu_ready.code == "teacher_feature_extraction_ready"


def test_preflight_rejects_wrong_model_identity_and_low_storage() -> None:
    wrong_model = evaluate_teacher_preflight(
        _probe(model_id="some/other-model"), mode="full_train"
    )
    low_storage = evaluate_teacher_preflight(
        _probe(free_storage_bytes=1), mode="full_train"
    )

    assert wrong_model.code == "teacher_model_identity_mismatch"
    assert low_storage.code == "insufficient_local_storage"


def test_cpu_smoke_cli_reports_fixture_scope_without_credentials(capsys: object) -> None:
    assert main(["--config", str(CONFIG_PATH), "--mode", "cpu_smoke"]) == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["code"] == "cpu_smoke_ready"
    assert payload["evidence_scope"] == "fixture_encoder_shapes_only"
    assert "token" not in captured.out.casefold()
