# Tamil Phoneme CTC Baseline Model Card

## Status

Engineering scaffold; no production model is bundled. Not clinically validated.

## Intended use

The future artifact will convert validated mono 16 kHz Tamil word-practice audio into frame-level
phoneme log probabilities for forced alignment and GOP scoring on the same edge device.

## Candidate source encoder

AI4Bharat `indicconformer_stt_ta_hybrid_ctc_rnnt_large` is recorded as a Tamil-aware teacher or
baseline candidate. Its existing text-ASR output vocabulary is not the required reviewed Tamil
phoneme inventory. A separately trained/exported phoneme CTC head and documented licence review are
required before release.

## Prohibited uses

- ASD detection, screening, diagnosis, severity prediction, or treatment decisions;
- open-ended transcription as the pronunciation score;
- cloud inference or upload of audio and voice-derived representations;
- performance or clinical claims based only on synthetic, adult, or proxy data.

## Required inputs before model release

- Tamil-expert-reviewed phoneme inventory, blank symbol, length, and gemination conventions;
- licensed training/validation data with participant-level splits;
- frozen therapist-labelled calibration and target-user test sets;
- an approved source checkpoint and reproducible export adapter;
- target Android tablet hardware.

## Implemented software evidence

- manifest SHA-256 validation before model load;
- explicit execution-provider selection;
- real synthetic ONNX inference test;
- frame shape, version, blank, finiteness, and normalization checks;
- GOP/confidence/syllable tests against literal expected values;
- non-overwriting dynamic INT8 tool and FP32/INT8 comparison logic;
- benchmark tooling for cold load, model size, peak process RSS, median, and P95 latency.

## Measurements not yet available

- phoneme error rate;
- forced-alignment boundary accuracy;
- therapist-score Pearson or Spearman correlation;
- calibration error and false-accept rate;
- FP32 versus INT8 score degradation for an approved model;
- target-tablet cold start, median/P95 latency, memory, battery, and thermal behavior;
- subgroup and target-user results.

These fields remain unavailable rather than being populated with synthetic claims.

