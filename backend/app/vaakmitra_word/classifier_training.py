"""Deterministic balanced classifier training for word-level embeddings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.linear_model import LogisticRegression

from .classifier import ClassifierArtifact


class ClassifierTrainingError(RuntimeError):
    """The governed classifier inputs cannot produce a valid artifact."""


@dataclass(frozen=True)
class TrainingExample:
    sample_id: str
    speaker_pseudonym: str
    label: str
    split: str
    embedding: np.ndarray


@dataclass(frozen=True)
class ClassifierTrainingReport:
    train_counts: dict[str, int]
    class_weights: dict[str, float]
    evaluation_accuracy: float
    evaluation_log_loss: float
    temperature: float
    evaluation_confusion_matrix: tuple[tuple[int, ...], ...]


def save_classifier_artifact(path: Path | str, artifact: ClassifierArtifact) -> None:
    destination = Path(path)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f"{destination.name}.part")
    if partial.exists():
        raise FileExistsError(partial)
    payload = {
        "version": np.asarray(artifact.version),
        "model_hash": np.asarray(artifact.model_hash),
        "vocabulary_hash": np.asarray(artifact.vocabulary_hash),
        "labels": np.asarray(artifact.labels),
        "weights": artifact.weights,
        "bias": artifact.bias,
        "pooling_schema": np.asarray(artifact.pooling_schema),
        "temperature": np.asarray(artifact.temperature),
    }
    if artifact.feature_means is not None:
        payload["feature_means"] = artifact.feature_means
        payload["feature_scales"] = artifact.feature_scales
    try:
        with partial.open("xb") as sink:
            np.savez_compressed(sink, **payload)
        partial.replace(destination)
    except Exception:
        if partial.exists():
            partial.unlink()
        raise


def pool_embedding(embedding: np.ndarray, *, schema: str = "mean-std-v1") -> np.ndarray:
    frames = np.asarray(embedding, dtype=np.float64)
    if frames.ndim != 2 or frames.shape[0] == 0 or frames.shape[1] == 0:
        raise ClassifierTrainingError("embedding_invalid")
    if not np.isfinite(frames).all():
        raise ClassifierTrainingError("embedding_non_finite")
    if schema == "mean-v1":
        return frames.mean(axis=0)
    if schema == "mean-std-v1":
        return np.concatenate((frames.mean(axis=0), frames.std(axis=0)))
    raise ClassifierTrainingError("pooling_schema_unsupported")


def _validate_sha256(name: str, value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise ClassifierTrainingError(f"{name}_invalid")
    return normalized


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    values = np.exp(shifted)
    return values / values.sum(axis=1, keepdims=True)


def train_classifier(
    examples: list[TrainingExample] | tuple[TrainingExample, ...],
    *,
    labels: tuple[str, ...],
    model_hash: str,
    vocabulary_hash: str,
    seed: int = 17,
) -> tuple[ClassifierArtifact, ClassifierTrainingReport]:
    if "OTHER" not in labels:
        raise ClassifierTrainingError("other_class_required")
    if not labels or len(set(labels)) != len(labels):
        raise ClassifierTrainingError("labels_invalid")
    model_hash = _validate_sha256("model_hash", model_hash)
    vocabulary_hash = _validate_sha256("vocabulary_hash", vocabulary_hash)

    ordered = sorted(examples, key=lambda item: (item.sample_id, item.speaker_pseudonym))
    if not ordered or len({item.sample_id for item in ordered}) != len(ordered):
        raise ClassifierTrainingError("training_sample_ids_invalid")
    speaker_splits: dict[str, str] = {}
    dimensions: set[int] = set()
    by_split: dict[str, list[tuple[np.ndarray, str]]] = {
        "train": [],
        "calibration": [],
        "evaluation": [],
    }
    for example in ordered:
        if example.label not in labels:
            raise ClassifierTrainingError("training_label_not_registered")
        if example.split not in by_split:
            raise ClassifierTrainingError("training_split_invalid")
        prior_split = speaker_splits.setdefault(example.speaker_pseudonym, example.split)
        if prior_split != example.split:
            raise ClassifierTrainingError("speaker_split_leakage")
        feature = pool_embedding(example.embedding, schema="mean-std-v1")
        dimensions.add(feature.shape[0])
        by_split[example.split].append((feature, example.label))
    if len(dimensions) != 1:
        raise ClassifierTrainingError("embedding_dimension_mismatch")
    for split, rows in by_split.items():
        present = {label for _, label in rows}
        if present != set(labels):
            raise ClassifierTrainingError(f"{split}_missing_labels")

    train_x = np.vstack([feature for feature, _ in by_split["train"]])
    train_y = np.asarray([label for _, label in by_split["train"]])
    feature_means = train_x.mean(axis=0)
    feature_scales = train_x.std(axis=0)
    feature_scales = np.where(feature_scales > 1e-12, feature_scales, 1.0)
    standardized_train = (train_x - feature_means) / feature_scales

    train_counts = {label: int(np.sum(train_y == label)) for label in sorted(labels)}
    total = len(train_y)
    class_weights = {
        label: total / (len(labels) * count)
        for label, count in train_counts.items()
    }
    estimator = LogisticRegression(
        class_weight=class_weights,
        max_iter=1000,
        random_state=seed,
        solver="lbfgs",
    )
    estimator.fit(standardized_train, train_y)
    if len(estimator.classes_) == 2:
        binary_rows = {
            str(estimator.classes_[0]): (-0.5 * estimator.coef_[0], -0.5 * estimator.intercept_[0]),
            str(estimator.classes_[1]): (0.5 * estimator.coef_[0], 0.5 * estimator.intercept_[0]),
        }
        weights = np.vstack([binary_rows[label][0] for label in labels])
        bias = np.asarray([binary_rows[label][1] for label in labels])
    else:
        class_indices = [list(estimator.classes_).index(label) for label in labels]
        weights = estimator.coef_[class_indices]
        bias = estimator.intercept_[class_indices]

    calibration_x = np.vstack([feature for feature, _ in by_split["calibration"]])
    calibration_y = np.asarray([labels.index(label) for _, label in by_split["calibration"]])
    calibration_logits = ((calibration_x - feature_means) / feature_scales) @ weights.T + bias

    def negative_log_likelihood(temperature: float) -> float:
        probabilities = _softmax(calibration_logits / temperature)
        return float(-np.log(np.maximum(probabilities[np.arange(len(calibration_y)), calibration_y], 1e-12)).mean())

    optimized = minimize_scalar(
        negative_log_likelihood,
        bounds=(0.25, 4.0),
        method="bounded",
        options={"xatol": 1e-8},
    )
    temperature = float(optimized.x) if optimized.success else 1.0

    evaluation_x = np.vstack([feature for feature, _ in by_split["evaluation"]])
    evaluation_y = np.asarray([labels.index(label) for _, label in by_split["evaluation"]])
    evaluation_logits = ((evaluation_x - feature_means) / feature_scales) @ weights.T + bias
    probabilities = _softmax(evaluation_logits / temperature)
    predictions = probabilities.argmax(axis=1)
    accuracy = float(np.mean(predictions == evaluation_y))
    log_loss = float(-np.log(np.maximum(probabilities[np.arange(len(evaluation_y)), evaluation_y], 1e-12)).mean())
    confusion = np.zeros((len(labels), len(labels)), dtype=np.int64)
    for actual, predicted in zip(evaluation_y, predictions, strict=True):
        confusion[actual, predicted] += 1

    artifact = ClassifierArtifact(
        version="word-linear-mean-std-v1",
        model_hash=model_hash,
        vocabulary_hash=vocabulary_hash,
        labels=labels,
        weights=weights,
        bias=bias,
        pooling_schema="mean-std-v1",
        feature_means=feature_means,
        feature_scales=feature_scales,
        temperature=temperature,
    )
    report = ClassifierTrainingReport(
        train_counts=train_counts,
        class_weights=class_weights,
        evaluation_accuracy=accuracy,
        evaluation_log_loss=log_loss,
        temperature=temperature,
        evaluation_confusion_matrix=tuple(tuple(int(value) for value in row) for row in confusion),
    )
    return artifact, report
