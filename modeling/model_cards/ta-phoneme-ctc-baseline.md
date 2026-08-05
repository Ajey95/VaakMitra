# Tamil Phoneme CTC Baseline Model Card

## Status

Technical prototype; no production model is bundled. Not clinically validated.

## Intended use

The runtime converts validated mono 16 kHz audio into frame-level CTC log probabilities for forced
alignment and GOP scoring. The recorded trained artifact is an adult-data proxy experiment and is
not approved for child feedback.

## Candidate source encoder

AI4Bharat `indicconformer_stt_ta_hybrid_ctc_rnnt_large` is recorded as a Tamil-aware teacher or
baseline candidate. Its existing text-ASR output vocabulary is not the required reviewed Tamil
phoneme inventory. A separately trained/exported phoneme CTC head and documented licence review are
required before release.

The research configuration pins revision `8c31aa8d04964b8fc87e4eaaee7916f7d2c024da` and records the
MIT model-card licence. Safe local teacher-feature caching is implemented for distillation
preparation, but no gated model or dataset is automatically downloaded and no direct phoneme
posterior capability is claimed.

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
- immutable CC0 adult-Tamil source audit and deterministic speaker-disjoint re-splitting;
- bounded raw-waveform proxy CTC training with pinned CPU dependencies and dynamic ONNX export;
- real proxy-model FP32/INT8 output comparison and development-laptop benchmark;
- provisional Epitran inventory generation and fail-closed IndicVoices/Vistaar preflight;
- local-only hash-linked teacher-feature cache validation; and
- official static ONNX Runtime mobile analysis with an explicit CPU-provider recommendation.

## Recorded proxy experiment

- data: 42 train, 8 validation, and 8 test utterances from 14/4/4 disjoint adult speakers;
- model: 16,112 parameters, 32 proxy Unicode units, 70,757-byte FP32 ONNX;
- test phone-unit error rate: `0.9819819819819819`; exact sequence accuracy: `0.0`;
- INT8 size: 48,679 bytes (`0.68797` of FP32);
- maximum posterior delta: `0.00008893385529518127`;
- INT8 laptop benchmark: 223.6853 ms cold load, 0.78375 ms median, 2.9517 ms P95,
  68,829,184-byte peak process RSS.
- NNAPI static compatibility: 8/51 nodes across 5 partitions as-is; not recommended.

These numbers validate tooling only. In particular, the error rate rejects this small proxy model
as a pronunciation-scoring candidate. The INT8 GOP delta is unavailable because Member 1 has not
provided validated alignment for this fixture.

## Measurements not yet available

- forced-alignment boundary accuracy;
- therapist-score Pearson or Spearman correlation;
- calibration error and false-accept rate;
- FP32 versus INT8 GOP degradation for an approved aligned model;
- target-tablet cold start, median/P95 latency, memory, battery, and thermal behavior;
- subgroup and target-user results.

These fields remain unavailable rather than being populated with synthetic claims.

## Dual-track strengthening evidence

The full phoneme-head wrapper, finite CTC loss, staged freeze policy, pinned configuration, and
deterministic CPU smoke are implemented. The CPU smoke uses a 148-parameter fixture encoder; it
does not load or train IndicConformer. A real checkpoint and adult-Tamil metrics remain GPU-job
outputs.

Additional implemented evidence includes:

- three-source PHOIBLE Tamil consensus with pinned Epitran provenance and conflict reporting;
- leakage-proof speaker/utterance/audio-digest corpus indexing for IISc-MILE/OpenSLR 127;
- compact Conformer and Conv-BiGRU students with representation and relational distillation;
- dynamic FP32 and INT8 ONNX execution for both student fixtures;
- controlled-confusion calibration with AUROC, Brier, ECE, FAR, FRR, bootstrap, and grouped
  thresholds;
- an 11-condition child-like transformation matrix explicitly labelled non-child evidence;
- pass/fail/not-measured promotion gates; and
- physical Android benchmark ingestion with emulator rejection.

## Current dual-track decision

No model is promoted. The full reference has no gated checkpoint, CUDA training run, adult-Tamil
PER, or calibrated confusion metrics. The two student fixtures prove architecture, loss, export,
INT8, and runtime compatibility, but are not teacher-distilled checkpoints and have no adult-Tamil
quality or physical-device evidence. `dual-track-cpu-comparison.json` records every absent value as
`not_measured`.
