from __future__ import annotations

import pytest

from vaakmitra.privacy.safe_logging import safe_log_event


@pytest.mark.parametrize(
    "forbidden_field",
    ["audio", "waveform", "embedding", "log_probabilities", "transcript", "child_name"],
)
def test_safe_log_event_rejects_voice_derived_fields(forbidden_field: str) -> None:
    with pytest.raises(ValueError, match="forbidden"):
        safe_log_event("inference", {forbidden_field: [0.1], "model_version": "v1"})


def test_safe_log_event_returns_allow_listed_copy() -> None:
    fields = {
        "attempt_id": "ATT-1",
        "model_version": "v1",
        "status": "ok",
        "latency_ms": 17.5,
        "tensor_shape": [24, 8],
    }

    event = safe_log_event("inference_complete", fields)

    assert event == {"event": "inference_complete", **fields}
    assert event is not fields
