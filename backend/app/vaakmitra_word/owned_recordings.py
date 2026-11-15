"""Conservative descriptive labels for the owner-provided evaluation recordings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class OwnedRecordingLabel:
    speaker_role: str
    speaker_pseudonym: str
    content_kind: str
    permitted_use: str
    canonical_word_id: None = None
    reference_eligible: bool = False
    role_evidence: str = "filename_series"


_THERAPIST_TASK_PREFIXES = ("sir", "dtw", "spontaneous", "syllable")
_VOCALIZATION_TOKENS = {"aa", "eaa", "ii", "laa", "raa", "taa", "uu", "voo"}


def classify_recording_name(filename: str) -> OwnedRecordingLabel:
    stem = Path(filename).stem.casefold().strip()
    compact = re.sub(r"[^a-z0-9]+", "", stem)
    if "noise" in compact:
        return OwnedRecordingLabel(
            speaker_role="environment",
            speaker_pseudonym="owned-environment-001",
            content_kind="environmental_noise",
            permitted_use="negative_canary_candidate",
        )

    if stem.startswith("1"):
        role = "child"
        pseudonym = "owned-child-001"
        permitted_use = "child_validation_only"
        task_name = compact[1:]
    elif stem.startswith(_THERAPIST_TASK_PREFIXES):
        role = "adult_therapist"
        pseudonym = "owned-therapist-001"
        permitted_use = "adult_engineering_evaluation"
        task_name = compact[3:] if compact.startswith("sir") else compact
    else:
        return OwnedRecordingLabel(
            speaker_role="unknown",
            speaker_pseudonym="owned-unknown-001",
            content_kind="unknown",
            permitted_use="review_required",
            role_evidence="no_supported_filename_series",
        )

    if "spontaneous" in task_name:
        content_kind = "spontaneous_speech"
    elif "syllable" in task_name:
        content_kind = "syllable_sequence"
    elif "dtw" in task_name:
        content_kind = "prompt_sequence"
    elif "word" in task_name:
        content_kind = "word_sequence"
    elif task_name in _VOCALIZATION_TOKENS:
        content_kind = "vocalization"
    else:
        content_kind = "unknown"
        permitted_use = "review_required"

    return OwnedRecordingLabel(
        speaker_role=role,
        speaker_pseudonym=pseudonym,
        content_kind=content_kind,
        permitted_use=permitted_use,
    )
