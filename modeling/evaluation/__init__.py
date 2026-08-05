"""Reproducible aggregate evaluation for phoneme CTC outputs."""

from modeling.evaluation.ctc_metrics import (
    CtcEvaluationReport,
    EvaluationRecord,
    collapse_ctc_tokens,
    edit_distance,
    evaluate_records,
)

__all__ = [
    "CtcEvaluationReport",
    "EvaluationRecord",
    "collapse_ctc_tokens",
    "edit_distance",
    "evaluate_records",
]

