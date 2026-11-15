"""Closed-vocabulary linear classifier over pooled encoder frames (CLS-001..005)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .contracts import EvidenceItem, WordCandidate


@dataclass(frozen=True)
class ClassifierArtifact:
    version: str
    model_hash: str
    vocabulary_hash: str
    labels: tuple[str, ...]
    weights: np.ndarray
    bias: np.ndarray
    pooling_schema: str = "mean-v1"
    feature_means: np.ndarray | None = None
    feature_scales: np.ndarray | None = None
    temperature: float = 1.0

    def __post_init__(self) -> None:
        weights = np.asarray(self.weights, dtype=np.float64)
        bias = np.asarray(self.bias, dtype=np.float64)
        if not self.labels or "OTHER" not in self.labels or len(set(self.labels)) != len(self.labels):
            raise ValueError("classifier labels must be unique and include OTHER")
        if weights.ndim != 2 or weights.shape[0] != len(self.labels):
            raise ValueError("weights must have one row per label")
        if bias.shape != (len(self.labels),):
            raise ValueError("bias must have one value per label")
        if not np.isfinite(weights).all() or not np.isfinite(bias).all():
            raise ValueError("classifier parameters must be finite")
        if self.pooling_schema not in {"mean-v1", "mean-std-v1"}:
            raise ValueError("unsupported pooling schema")
        if self.pooling_schema == "mean-std-v1" and weights.shape[1] % 2:
            raise ValueError("mean-std weights must have an even feature width")
        if not np.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError("temperature must be positive and finite")
        means = None if self.feature_means is None else np.asarray(self.feature_means, dtype=np.float64)
        scales = None if self.feature_scales is None else np.asarray(self.feature_scales, dtype=np.float64)
        if (means is None) != (scales is None):
            raise ValueError("feature means and scales must be provided together")
        if means is not None:
            if means.shape != (weights.shape[1],) or scales.shape != (weights.shape[1],):
                raise ValueError("feature statistics must match classifier feature width")
            if not np.isfinite(means).all() or not np.isfinite(scales).all() or np.any(scales <= 0):
                raise ValueError("feature statistics must be finite with positive scales")
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "bias", bias)
        object.__setattr__(self, "feature_means", means)
        object.__setattr__(self, "feature_scales", scales)


@dataclass(frozen=True)
class ClassificationResult:
    evidence: EvidenceItem
    candidates: tuple[WordCandidate, ...] = ()
    entropy: float | None = None


class LinearWordClassifier:
    def __init__(self, artifact: ClassifierArtifact):
        self.artifact = artifact
        self.version = artifact.version

    def predict(self, embeddings: np.ndarray, word_id: str) -> ClassificationResult:
        if word_id not in self.artifact.labels:
            return ClassificationResult(
                EvidenceItem(available=False, reason="target_not_in_classifier_vocabulary")
            )
        frames = np.asarray(embeddings, dtype=np.float64)
        expected_dimensions = self.artifact.weights.shape[1]
        if self.artifact.pooling_schema == "mean-std-v1":
            expected_dimensions //= 2
        if frames.ndim != 2 or frames.shape[0] == 0 or frames.shape[1] != expected_dimensions:
            return ClassificationResult(EvidenceItem(available=False, reason="invalid_embedding_shape"))
        if not np.isfinite(frames).all():
            return ClassificationResult(EvidenceItem(available=False, reason="invalid_embeddings"))
        if self.artifact.pooling_schema == "mean-std-v1":
            pooled = np.concatenate((frames.mean(axis=0), frames.std(axis=0)))
        else:
            pooled = frames.mean(axis=0)
        if self.artifact.feature_means is not None:
            pooled = (pooled - self.artifact.feature_means) / self.artifact.feature_scales
        logits = (self.artifact.weights @ pooled + self.artifact.bias) / self.artifact.temperature
        logits -= float(np.max(logits))
        probabilities = np.exp(logits)
        probabilities /= float(np.sum(probabilities))
        order = np.argsort(-probabilities)
        candidates = tuple(
            WordCandidate(word=self.artifact.labels[index], probability=float(probabilities[index]))
            for index in order
        )
        target_probability = float(probabilities[self.artifact.labels.index(word_id)])
        raw_entropy = float(-np.sum(probabilities * np.log(np.maximum(probabilities, 1e-12))))
        entropy = raw_entropy / float(np.log(len(probabilities))) if len(probabilities) > 1 else 0.0
        entropy = min(1.0, max(0.0, entropy))
        return ClassificationResult(
            EvidenceItem(available=True, target_probability=target_probability),
            candidates,
            entropy,
        )
