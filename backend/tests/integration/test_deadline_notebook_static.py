from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

NOTEBOOK = Path("notebooks/VaakMitra_GPU_Training_Colab.ipynb")


def _load_notebook() -> dict[str, Any]:
    payload: Any = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def _cell_code(notebook: dict[str, Any], cell_id: str) -> str:
    cell = next(cell for cell in notebook["cells"] if cell["id"] == cell_id)
    return "".join(cell["source"])


def test_deadline_notebook_runs_canary_before_reference_training() -> None:
    notebook = _load_notebook()
    ids = [cell["id"] for cell in notebook["cells"]]
    assert ids.index("gpu-canary") < ids.index("reference-head-training")
    contract = notebook["metadata"]["vaakmitra_gpu_contract"]
    assert contract["default_profile"] == "deadline_7day"
    assert contract["checkpoint_every_updates"] == 500
    assert contract["maximum_students"] == 1


def test_deadline_notebook_exports_reference_before_optional_student_work() -> None:
    notebook = _load_notebook()
    ids = [cell["id"] for cell in notebook["cells"]]
    assert ids.index("reference-head-training") < ids.index("reference-head-export")
    assert ids.index("reference-head-export") < ids.index("reference-adaptive-training")
    assert ids.index("reference-final-export") < ids.index("teacher-features")


def test_deadline_notebook_uses_checked_in_training_controls() -> None:
    notebook = _load_notebook()
    code = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    for module in (
        "batch_order",
        "canary",
        "deadline_profile",
        "reference_artifact",
        "reference_stage",
        "resume_checkpoint",
        "session_control",
    ):
        assert "modeling." in code and module in code
    assert "maximum_unknown_phone_record_rate" in code
    assert "deferred_by_deadline_profile" in code


def test_test_split_is_not_evaluated_before_final_reference_selection() -> None:
    notebook = _load_notebook()
    final_export_index = [cell["id"] for cell in notebook["cells"]].index(
        "reference-final-export"
    )
    preceding_code = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"][:final_export_index]
        if cell["cell_type"] == "code"
    )
    assert 'items_by_split["test"]' not in preceding_code
    assert 'items_by_split["test"]' in _cell_code(notebook, "reference-final-export")
