# Member 2 Speech Intelligence Architecture

## Scope boundary

Member 2 owns local acoustic inference, the phoneme CTC probability contract, GOP/confidence
scoring, syllable aggregation, model integrity, export/quantization tooling, and benchmark evidence.

Member 2 does not capture audio, run VAD, normalize Tamil text, generate expected phonemes, force
align frames, choose exercises, persist attempts, synchronize metrics, or implement Unity and
therapist APIs.

## Two-phase processing

```text
Member 1 validated mono 16 kHz audio
                |
                v
AssessmentPipeline.infer
                |
                v
AcousticOutput [frames, vocabulary] log probabilities
                |
                v
Member 1 forced alignment against expected phonemes
                |
                v
AssessmentPipeline.score_aligned_attempt
                |
                v
Member 2 phoneme GOP + confidence + syllable aggregates
                |
                v
Member 3 receives AssessmentResult
```

The two calls prevent Member 2 from retaining or recomputing audio while Member 1 aligns the
probability matrix. Neither `AcousticOutput` nor its probability matrix belongs in persistence or
sync payloads.

## Dual-track model lifecycle

Both strategies feed the same `AcousticOutput` contract:

```text
PHOIBLE + Epitran candidate vocabulary
             +
speaker/audio-disjoint adult Tamil corpus
             |
             v
Strategy 2: IndicConformer encoder + new phoneme CTC head
             |
             +---- accuracy/reference ceiling
             |
             v
teacher hidden representations (local, hash-bound)
             |
             v
Strategy 1: compact Conformer and Conv-BiGRU students
             |
             v
FP32 ONNX -> INT8 -> parity -> operator audit -> physical Android report
```

The teacher's text decoder is bypassed. Distillation operates on hidden acoustic representations
plus transcript-derived phoneme CTC targets; text-token posteriors are not compared with phoneme
posteriors. Every model is evaluated through the same adult-PER, controlled-confusion, calibration,
transformation, quantization, and edge gates.

On a CPU-only host, the pipeline validates data, shapes, freeze stages, losses, student training,
export, quantization, runtime, and reports. Real full-teacher training and complete-corpus
teacher-feature/student training remain CUDA jobs.

## Runtime contract

`OnnxAcousticModelRuntime` verifies the packaged file against the manifest SHA-256 before creating
an ONNX Runtime session. Execution providers are explicit; unavailable providers fail instead of
silently falling back. The runtime accepts only finite one-dimensional floating-point audio at
16 kHz and emits:

- float log probabilities shaped `[frames, vocabulary_size]`;
- positive `frame_shift_ms`;
- explicit `blank_index`;
- independently versioned model and vocabulary identifiers.

If a model produces logits, the adapter applies a stable log-softmax. The pipeline then checks
per-frame probability normalization before exposing output to Member 1.

## GOP baseline

For an aligned expected phoneme, the scorer calculates the mean expected log posterior and the
strongest mean non-blank competitor. The sigmoid of that margin is the baseline GOP score. This is
traceable engineering evidence, not therapist calibration.

Confidence combines absolute acoustic separation with Member 1's segment confidence. Confidence is
gated before score categories, so uncertain evidence becomes `unscorable`. Configured categories are
`pass`, `coach`, `retry`, and `unscorable`; Member 3 owns the mapping to avatar or exercise actions.

## Privacy behavior

The runtime package contains no HTTP client. Allow-listed logs may include versions, status/reason
codes, tensor shapes, providers, and aggregate timing. Audio, embeddings, probability arrays,
transcripts, direct child identity, and diagnostic language are rejected from safe log records.

## Evidence limitations

Synthetic ONNX tests prove loading, integrity, tensor, and deterministic scoring behavior. A
separate CC0 adult-Tamil proxy run proves speaker-disjoint data preparation, CPU training, dynamic
ONNX export, INT8 conversion, and laptop benchmarking. Its 0.98198 test phone-unit error rate makes
it unsuitable for pronunciation scoring.

Neither evidence path proves expert inventory correctness, forced-alignment boundary accuracy,
therapist correlation, target-child validity, Android latency, memory, battery, or thermal behavior.
Those claims require Member 1 alignment integration, a reviewed Tamil inventory, substantially
better model evidence, therapist-labelled target-user data, and the actual target device.
