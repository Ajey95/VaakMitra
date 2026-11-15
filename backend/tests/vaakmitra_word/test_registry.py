from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.vaakmitra_word.contracts import ModelEvidence
from app.vaakmitra_word.registry import ArtifactSettings, ServiceRegistry


@dataclass
class FakeModel:
    model_version: str = "synthetic-model"
    model_hash: str = "synthetic-hash"
    ready: bool = True
    is_test_double: bool = True

    def infer(self, samples: np.ndarray, sample_rate: int, target_word: str) -> ModelEvidence:
        return ModelEvidence(
            target_probability=0.9,
            embeddings=np.ones((2, 2), dtype=np.float32),
            model_version=self.model_version,
            model_hash=self.model_hash,
        )


def settings(tmp_path: Path) -> ArtifactSettings:
    return ArtifactSettings(
        model_path=tmp_path / "missing.nemo",
        model_sha256="a" * 64,
        classifier_path=tmp_path / "missing-classifier.npz",
        reference_bank_path=tmp_path / "missing-references.npz",
        calibration_path=tmp_path / "missing-calibration.json",
    )


def test_missing_model_is_not_scoring_ready(tmp_path: Path) -> None:
    registry = ServiceRegistry(settings(tmp_path))

    readiness = registry.scoring_readiness()

    assert readiness.ready is False
    assert "model_unavailable" in readiness.reasons


def test_fake_model_is_engineering_ready_but_never_production_ready(tmp_path: Path) -> None:
    registry = ServiceRegistry(settings(tmp_path), model=FakeModel())

    readiness = registry.scoring_readiness()

    assert readiness.ready is False
    assert readiness.engineering_ready is True
    assert "test_model_not_production" in readiness.reasons

