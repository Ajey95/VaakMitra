# Adult Engineering Calibration

This stage fits and evaluates the evidence-fusion operating point using adult-only, speaker-disjoint data. It compares logistic output with an isotonic mapping on the calibration split, selects the lower-Brier candidate there, freezes retry/pass thresholds there, and reports final metrics only on the untouched evaluation split.

The artifact is deliberately emitted with `population=adult_only_engineering` and `approved=false`. It can demonstrate that the training, missing-value masks, metrics, confidence intervals, and bundle cross-hashes work. It cannot authorize child scoring, clinical use, or a `PASS` decision.

Input is JSON Lines. Every row must identify `population` as `adult`, and contain `sample_id`, `speaker_pseudonym`, `word_id`, `split`, `target_match`, and the frozen SSOT feature set: `p_raw_target`, `p_normalized_target`, `raw_normalized_disagreement`, `p_classifier_target`, `classifier_entropy`, `dtw_similarity`, `raw_top1_is_target`, `normalized_top1_is_target`, `duration_quality`, and `noise_quality`. A missing feature must be JSON `null`; the pipeline adds a separate missingness mask for every feature. Speakers may occur in only one of `train`, `calibration`, or `evaluation`.

Example invocation:

```powershell
python scripts/model/calibrate_engineering.py `
  --evidence-manifest D:\VaakMitraData\calibration\adult-evidence.jsonl `
  --model D:\VaakMitraRuntime\models\indicconformer_ta.nemo `
  --classifier D:\VaakMitraData\artifacts\word-classifier.npz `
  --reference-bank D:\VaakMitraData\artifacts\reference-bank.npz `
  --vocabulary backend\model_artifacts\tamil_word_registry_v1.json `
  --output D:\VaakMitraData\artifacts\adult-engineering-calibration.json `
  --report D:\VaakMitraData\reports\adult-engineering-calibration.json
```

Production remains blocked until a child-separated, therapist-labelled dataset passes the predeclared false-PASS objective and an authorized reviewer creates a distinct approved clinical artifact.
