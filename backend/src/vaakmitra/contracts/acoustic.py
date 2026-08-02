"""Acoustic inference output shared with the Member 1 forced aligner."""

from __future__ import annotations

from typing import Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AcousticOutput(BaseModel):
    """Validated metadata and frame-level CTC log probabilities."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    log_probabilities: np.ndarray
    frame_shift_ms: float = Field(gt=0)
    model_version: str = Field(min_length=1)
    vocabulary_version: str = Field(min_length=1)
    blank_index: int = Field(ge=0)
    vocabulary_size: int = Field(gt=1)

    @model_validator(mode="after")
    def validate_probability_tensor(self) -> Self:
        probabilities = self.log_probabilities
        if probabilities.ndim != 2:
            raise ValueError("log_probabilities must have shape [frames, vocabulary_size]")
        if probabilities.shape[0] == 0:
            raise ValueError("log_probabilities must contain at least one frame")
        if probabilities.shape[1] != self.vocabulary_size:
            raise ValueError("probability width must equal vocabulary_size")
        if self.blank_index >= self.vocabulary_size:
            raise ValueError("blank_index must be smaller than vocabulary_size")
        if not np.issubdtype(probabilities.dtype, np.floating):
            raise ValueError("log_probabilities must use a floating-point dtype")
        if not np.isfinite(probabilities).all():
            raise ValueError("log_probabilities must contain only finite values")
        return self

