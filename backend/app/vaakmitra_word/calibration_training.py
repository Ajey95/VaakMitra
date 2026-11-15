"""Deterministic adult-only engineering calibration and safety metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from .calibration import CalibrationArtifact


BASE_FEATURES = (
    "p_raw_target",
    "p_normalized_target",
    "raw_normalized_disagreement",
    "p_classifier_target",
    "classifier_entropy",
    "dtw_similarity",
    "raw_top1_is_target",
    "normalized_top1_is_target",
    "duration_quality",
    "noise_quality",
)


class CalibrationTrainingError(RuntimeError):
    """Calibration evidence violates an engineering governance constraint."""


@dataclass(frozen=True)
class CalibrationExample:
    sample_id: str
    speaker_pseudonym: str
    word_id: str
    split: str
    target_match: bool
    features: dict[str, float | None]


@dataclass(frozen=True)
class CalibrationTrainingReport:
    population: str
    approved: bool
    selected_model: str
    split_counts: dict[str, int]
    evaluation: dict[str, float]
    bootstrap_intervals: dict[str, tuple[float, float]]
    word_confusion: dict[str, dict[str, int]]


def _valid_hash(name: str, value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
        raise CalibrationTrainingError(f"{name}_invalid")
    return normalized


def _encode(example: CalibrationExample) -> np.ndarray:
    if set(example.features) != set(BASE_FEATURES):
        raise CalibrationTrainingError("calibration_feature_schema_mismatch")
    values: list[float] = []
    masks: list[float] = []
    for name in BASE_FEATURES:
        value = example.features[name]
        if value is None:
            values.append(0.0)
            masks.append(1.0)
        else:
            number = float(value)
            if not np.isfinite(number) or number < 0.0 or number > 1.0:
                raise CalibrationTrainingError("calibration_feature_invalid")
            values.append(number)
            masks.append(0.0)
    return np.asarray(values + masks, dtype=np.float64)


def _sigmoid(logits: np.ndarray) -> np.ndarray:
    clipped = np.clip(logits, -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _ece(labels: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    result = 0.0
    edges = np.linspace(0.0, 1.0, bins + 1)
    for index in range(bins):
        included = (probabilities >= edges[index]) & (
            probabilities <= edges[index + 1] if index == bins - 1 else probabilities < edges[index + 1]
        )
        if included.any():
            result += float(included.mean()) * abs(
                float(labels[included].mean()) - float(probabilities[included].mean())
            )
    return result


def _metrics(
    labels: np.ndarray,
    probabilities: np.ndarray,
    retry_threshold: float,
    pass_threshold: float,
) -> dict[str, float]:
    decisions = np.where(
        probabilities >= pass_threshold,
        1,
        np.where(probabilities <= retry_threshold, 0, -1),
    )
    negatives = labels == 0
    positives = labels == 1
    scored = decisions >= 0
    return {
        "accuracy": float(np.mean((decisions == labels) & scored)),
        "false_pass_rate": float(np.mean(decisions[negatives] == 1)),
        "false_retry_rate": float(np.mean(decisions[positives] == 0)),
        "abstention_rate": float(np.mean(decisions == -1)),
        "ece": _ece(labels, probabilities),
        "brier": float(brier_score_loss(labels, probabilities)),
        "auroc": float(roc_auc_score(labels, probabilities)),
        "auprc": float(average_precision_score(labels, probabilities)),
    }


def _bootstrap(
    labels: np.ndarray,
    probabilities: np.ndarray,
    retry_threshold: float,
    pass_threshold: float,
    *,
    seed: int,
    iterations: int = 250,
) -> dict[str, tuple[float, float]]:
    rng = np.random.default_rng(seed)
    collected: dict[str, list[float]] = {name: [] for name in ("accuracy", "false_pass_rate", "false_retry_rate", "abstention_rate", "ece", "brier")}
    for _ in range(iterations):
        indices = rng.integers(0, len(labels), size=len(labels))
        sampled_labels = labels[indices]
        if len(np.unique(sampled_labels)) < 2:
            continue
        sampled = _metrics(sampled_labels, probabilities[indices], retry_threshold, pass_threshold)
        for name in collected:
            collected[name].append(sampled[name])
    return {
        name: (float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975)))
        for name, values in collected.items()
        if values
    }


def train_adult_engineering_calibration(
    examples: list[CalibrationExample] | tuple[CalibrationExample, ...],
    *,
    model_hash: str,
    classifier_hash: str,
    reference_bank_hash: str,
    vocabulary_hash: str,
    dataset_manifest_hash: str,
    seed: int = 17,
    vad_config_hash: str = '',
    live_pipeline_hash: str = '',
) -> tuple[CalibrationArtifact, CalibrationTrainingReport]:
    hashes = {
        name: _valid_hash(name, value)
        for name, value in {
            "model_hash": model_hash,
            "classifier_hash": classifier_hash,
            "reference_bank_hash": reference_bank_hash,
            "vocabulary_hash": vocabulary_hash,
            "dataset_manifest_hash": dataset_manifest_hash,
        }.items()
    }
    if vad_config_hash:
        _valid_hash('vad_config_hash', vad_config_hash)
    if live_pipeline_hash:
        live_pipeline_hash = _valid_hash('live_pipeline_hash', live_pipeline_hash)
    ordered = sorted(examples, key=lambda item: (item.sample_id, item.speaker_pseudonym))
    if not ordered or len({item.sample_id for item in ordered}) != len(ordered):
        raise CalibrationTrainingError("calibration_sample_ids_invalid")
    splits: dict[str, list[CalibrationExample]] = {"train": [], "calibration": [], "evaluation": []}
    speaker_splits: dict[str, str] = {}
    for example in ordered:
        if example.split not in splits:
            raise CalibrationTrainingError("calibration_split_invalid")
        previous = speaker_splits.setdefault(example.speaker_pseudonym, example.split)
        if previous != example.split:
            raise CalibrationTrainingError("speaker_split_leakage")
        _encode(example)
        splits[example.split].append(example)
    for name, rows in splits.items():
        if {row.target_match for row in rows} != {False, True}:
            raise CalibrationTrainingError(f"{name}_missing_outcome")

    feature_order = BASE_FEATURES + tuple(f"missing__{name}" for name in BASE_FEATURES)
    train_x = np.vstack([_encode(item) for item in splits["train"]])
    train_y = np.asarray([int(item.target_match) for item in splits["train"]], dtype=np.int64)
    means = train_x.mean(axis=0)
    scales = train_x.std(axis=0)
    scales = np.where(scales > 1e-12, scales, 1.0)
    estimator = LogisticRegression(class_weight="balanced", random_state=seed, solver="lbfgs", max_iter=1000)
    estimator.fit((train_x - means) / scales, train_y)
    coefficients = estimator.coef_[0]
    intercept = float(estimator.intercept_[0])

    calibration_x = np.vstack([_encode(item) for item in splits["calibration"]])
    calibration_y = np.asarray([int(item.target_match) for item in splits["calibration"]], dtype=np.int64)
    base_calibration = _sigmoid(((calibration_x - means) / scales) @ coefficients + intercept)
    isotonic = IsotonicRegression(out_of_bounds="clip")
    isotonic_probabilities = isotonic.fit_transform(base_calibration, calibration_y)
    logistic_brier = float(brier_score_loss(calibration_y, base_calibration))
    isotonic_brier = float(brier_score_loss(calibration_y, isotonic_probabilities))
    use_isotonic = isotonic_brier + 1e-12 < logistic_brier
    selected_calibration = isotonic_probabilities if use_isotonic else base_calibration
    model_kind = "logistic_isotonic" if use_isotonic else "logistic"
    isotonic_x = tuple(float(value) for value in isotonic.X_thresholds_) if use_isotonic else ()
    isotonic_y = tuple(float(value) for value in isotonic.y_thresholds_) if use_isotonic else ()

    negative_scores = selected_calibration[calibration_y == 0]
    positive_scores = selected_calibration[calibration_y == 1]
    retry_threshold = float(np.max(negative_scores))
    pass_threshold = float(np.min(positive_scores))
    if retry_threshold >= pass_threshold:
        midpoint = float(np.median(selected_calibration))
        retry_threshold = max(0.0, midpoint - 0.05)
        pass_threshold = min(1.0, midpoint + 0.05)
    if retry_threshold >= pass_threshold:
        raise CalibrationTrainingError("adult_operating_point_unavailable")

    evaluation_x = np.vstack([_encode(item) for item in splits["evaluation"]])
    evaluation_y = np.asarray([int(item.target_match) for item in splits["evaluation"]], dtype=np.int64)
    evaluation_probabilities = _sigmoid(((evaluation_x - means) / scales) @ coefficients + intercept)
    if use_isotonic:
        evaluation_probabilities = np.interp(evaluation_probabilities, isotonic_x, isotonic_y)
    evaluation = _metrics(evaluation_y, evaluation_probabilities, retry_threshold, pass_threshold)
    intervals = _bootstrap(
        evaluation_y,
        evaluation_probabilities,
        retry_threshold,
        pass_threshold,
        seed=seed,
    )
    decisions = np.where(
        evaluation_probabilities >= pass_threshold,
        "PASS",
        np.where(evaluation_probabilities <= retry_threshold, "RETRY", "UNSCORABLE"),
    )
    word_confusion: dict[str, dict[str, int]] = {}
    for example, decision in zip(splits["evaluation"], decisions, strict=True):
        counts = word_confusion.setdefault(example.word_id, {"PASS": 0, "RETRY": 0, "UNSCORABLE": 0})
        counts[str(decision)] += 1

    artifact = CalibrationArtifact(
        version="adult-engineering-calibration-1",
        approved=False,
        population="adult_only_engineering",
        model_kind=model_kind,
        model_hash=hashes["model_hash"],
        classifier_hash=hashes["classifier_hash"],
        reference_bank_hash=hashes["reference_bank_hash"],
        vocabulary_hash=hashes["vocabulary_hash"],
        dataset_manifest_hash=hashes["dataset_manifest_hash"],
        vad_config_hash=vad_config_hash,
        live_pipeline_hash=live_pipeline_hash,
        feature_order=feature_order,
        feature_means=tuple(float(value) for value in means),
        feature_scales=tuple(float(value) for value in scales),
        coefficients=tuple(float(value) for value in coefficients),
        intercept=intercept,
        retry_threshold=retry_threshold,
        pass_threshold=pass_threshold,
        isotonic_x=isotonic_x,
        isotonic_y=isotonic_y,
    )
    report = CalibrationTrainingReport(
        population="adult_only_engineering",
        approved=False,
        selected_model=model_kind,
        split_counts={name: len(rows) for name, rows in splits.items()},
        evaluation=evaluation,
        bootstrap_intervals=intervals,
        word_confusion=word_confusion,
    )
    return artifact, report
