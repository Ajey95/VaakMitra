# Member 2 Proxy Validation and Edge Evidence Design

## Status and purpose

Approved on 5 August 2026 after confirming that the team has neither therapist-labelled Tamil
child recordings nor the target Android tablet. This addendum defines the strongest honest Member 2
technical-prototype completion path available with those inputs missing. It extends, and does not
replace, the 2 August Member 2 design.

## Completion boundary

Member 2 engineering is complete when the repository can validate licensed proxy-data provenance,
evaluate phoneme CTC predictions, fit auditable proxy confidence thresholds, export and compare
FP32/INT8 ONNX models, run development-hardware benchmarks, and assemble a machine-readable release
evidence bundle. Every command must run locally and be reproducible from versioned manifests.

The result remains a `technical_prototype` until both therapist-labelled target-user validation and
actual target-tablet measurements exist. Proxy/adult/synthetic evidence must never be relabelled as
clinical validation or target-device evidence.

## Data and licence design

Real audio and model weights stay outside Git. A checked-in corpus manifest records dataset identity,
immutable revision, source URL, declared licence, population, label origin, local-only processing,
split membership, and file hashes. Validation fails when the licence is absent, the revision is
mutable, child/therapist claims are attached to proxy data, or a speaker appears in more than one
split.

Approved proxy sources may be used only when their declared licence permits the intended academic
use. A source with no declared licence may be recorded as a rejected candidate but cannot become an
approved training or release dependency.

## Phoneme evaluation design

Evaluation consumes frozen JSONL records containing an utterance identifier, reference phoneme
sequence, predicted CTC token sequence, population label, and scorable flag. The evaluator performs
explicit blank removal and repeat collapse, computes edit distance and phoneme error rate, and
reports micro/macro PER, exact-sequence accuracy, counts, and unscorable rate. Adult/proxy and future
target-user results remain separate evidence scopes.

This evaluator measures a phoneme recognizer. It does not measure therapist agreement, clinical
effectiveness, or Member 1 forced-alignment boundary accuracy.

## Proxy calibration design

Calibration consumes frozen scalar GOP/confidence examples with binary engineering labels such as
clean reference versus controlled corruption. It selects deterministic pass/coach/retry thresholds
under a configured false-accept ceiling and reports the confusion counts and calibration error.
Reports carry `proxy_not_therapist_calibrated` and cannot be loaded as clinical calibration.

Runtime safety remains conservative: missing, mismatched, or weak evidence returns `unscorable` or
`retry`, never a confident negative judgement about a child.

## Edge and Android-ready evidence

The existing ONNX runtime, integrity checking, dynamic INT8 conversion, output comparison, and
benchmark runner remain the execution core. A release-evidence assembler links immutable hashes for
the model, vocabulary, corpus, evaluation, calibration, quantization comparison, and benchmark
reports. It labels laptop and emulator results as development evidence and refuses a
`target_device_validated` release unless an actual `target_device` benchmark and therapist evidence
are supplied.

The Android-ready output is a package manifest and operator/runtime checklist for ONNX Runtime
Mobile integration. Without the tablet it may prove packaging compatibility and CPU execution only;
latency, RSS, battery, and thermal acceptance remain unavailable.

## Privacy and ownership

No corpus audio, waveform arrays, embeddings, probability matrices, transcripts, or direct identity
enter Git, logs, evaluation reports, or release evidence. Only hashes, aggregate metrics, versioned
schemas, and synthetic fixtures are committed.

This addendum implements only Member 2 responsibilities. Tamil G2P and forced alignment remain
Member 1 work. Session policy, persistence, synchronization, Unity behavior, and therapist APIs
remain Member 3 work.

## Acceptance evidence

- Every new behavior is introduced through a failing automated test.
- Corpus and release validation reject missing licence/provenance and misleading evidence scopes.
- CTC evaluation is verified against literal edit-distance and collapse examples.
- Proxy calibration is deterministic and reports false accepts and unscorable examples.
- A synthetic ONNX fixture exercises FP32 inference, INT8 conversion, comparison, and laptop
  benchmarking end to end without being described as a Tamil production model.
- Full pytest, Ruff, strict mypy, package build, CLI smoke tests, and `git diff --check` pass.

