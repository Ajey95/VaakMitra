"""Create allow-listed log records without voice-derived or identifying data."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

_ALLOWED_FIELDS = frozenset(
    {
        "attempt_id",
        "duration_ms",
        "frame_count",
        "latency_ms",
        "model_version",
        "provider",
        "reason",
        "scoring_version",
        "status",
        "tensor_shape",
        "vocabulary_size",
        "vocabulary_version",
    }
)


def safe_log_event(event: str, fields: Mapping[str, Any]) -> dict[str, Any]:
    """Return a defensive copy of an allow-listed non-sensitive log event."""

    if not event.strip():
        raise ValueError("event name must not be empty")
    forbidden = sorted(set(fields) - _ALLOWED_FIELDS)
    if forbidden:
        raise ValueError(f"forbidden log fields: {', '.join(forbidden)}")
    return {"event": event, **deepcopy(dict(fields))}
