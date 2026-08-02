# Member 2 Speech Intelligence Design

## Purpose

This design defines only Backend Member 2's contribution to ASD-Edge-ST 2.0:

- a local Tamil-aware acoustic-model runtime;
- frame-level Tamil phoneme CTC log probabilities;
- phoneme GOP and confidence scoring after forced alignment;
- syllable aggregation and neutral low-confidence outcomes;
- ONNX export, INT8 comparison, model packaging, and reproducible benchmarks;
- Member 2 tests, contracts, model documentation, and integration evidence.

Audio capture, VAD, Tamil G2P, forced alignment, session orchestration, persistence, synchronization, Unity UI, therapist APIs, and adaptive exercise decisions remain owned by Members 1 and 3. Member 2 provides typed integration contracts for those components but does not implement them.

## Delivery Strategy

The repository is empty, while the PRD leaves the final Tamil phoneme inventory and deployable phoneme-model artifact open. Implementation will therefore be contract-first and model-pluggable:

1. Establish a production-shaped Python 3.11 repository and stable typed contracts.
2. Implement deterministic CTC validation, GOP scoring, confidence gating, and syllable aggregation against hand-checked fixtures.
3. Implement an ONNX Runtime adapter that loads a locally packaged model and validates its metadata, hash, inputs, and outputs.
4. Keep the AI4Bharat Tamil IndicConformer as a teacher/baseline candidate rather than claiming that its ASR vocabulary is already the required Tamil phoneme head.
5. Add export, quantization, equivalence, and benchmark tooling that becomes executable when an approved trained model is placed in the ignored artifact directory.

This produces testable Member 2 software immediately without inventing clinical accuracy or bundling an unapproved model.

## Repository Structure

```text
VaakMitra/
|-- README.md
|-- .gitignore
|-- backend/
|   |-- pyproject.toml
|   |-- configs/
|   |   |-- model.example.json
|   |   `-- scoring.default.json
|   |-- src/vaakmitra/
|   |   |-- __init__.py
|   |   |-- contracts/
|   |   |   |-- acoustic.py
|   |   |   |-- alignment.py
|   |   |   `-- scoring.py
|   |   |-- acoustic/
|   |   |   |-- base.py
|   |   |   |-- metadata.py
|   |   |   `-- onnx_runtime.py
|   |   |-- ctc/
|   |   |   |-- vocabulary.py
|   |   |   `-- probabilities.py
|   |   |-- scoring/
|   |   |   |-- gop.py
|   |   |   |-- confidence.py
|   |   |   `-- syllables.py
|   |   |-- pipeline/
|   |   |   `-- assessment.py
|   |   `-- privacy/
|   |       `-- safe_logging.py
|   `-- tests/
|       |-- unit/
|       |-- contracts/
|       |-- integration/
|       `-- fixtures/
|-- modeling/
|   |-- configs/
|   |-- training/
|   |-- export/
|   |-- quantization/
|   |-- validation/
|   |-- manifests/
|   |-- model_cards/
|   `-- artifacts/
|       `-- README.md
|-- benchmarks/
|   |-- fixtures/
|   |-- manifests/
|   `-- reports/
|-- docs/
|   |-- architecture/
|   |-- contracts/
|   `-- superpowers/
`-- scripts/
```

Large model weights, real child audio, embeddings, and probability matrices are excluded from Git. Only schemas, synthetic fixtures, manifests, hashes, model cards, and aggregate benchmark reports may be committed.

## Runtime Architecture

### Acoustic runtime

`AcousticModelRuntime` is a protocol with a single inference responsibility. It consumes a validated mono 16 kHz floating-point waveform supplied in memory by Member 1 and returns an `AcousticOutput` containing:

- `log_probabilities`: float32 tensor shaped `[frames, vocabulary_size]`;
- `frame_shift_ms`: positive frame duration used by the aligner;
- `model_version`: independently traceable semantic version;
- `vocabulary_version`: independently traceable version;
- `blank_index`: valid index into the vocabulary;
- non-sensitive timing metadata.

The runtime rejects empty audio, non-finite samples, unsupported sample rates, invalid model hashes, missing metadata, mismatched tensor ranks, unexpected vocabulary dimensions, and non-finite model outputs. It never resamples, persists, uploads, or logs audio because those responsibilities are outside Member 2.

`OnnxAcousticModelRuntime` loads only a local model whose SHA-256 digest matches its manifest. CPU is the deterministic default execution provider. Other providers may be selected explicitly for benchmark runs, but the output contract remains identical.

### Phoneme CTC contract

The vocabulary is a versioned ordered list with one explicit blank symbol. The first committed vocabulary is a contract fixture, not a declaration that the Tamil expert review is complete. Runtime validation guarantees:

- vocabulary tokens are unique and non-empty;
- exactly one blank token exists;
- the blank index matches model metadata;
- every frame contains one value per vocabulary token;
- log probabilities are finite and normalize to approximately one in probability space;
- frame timing is deterministic and positive.

Member 1 consumes this probability matrix for forced alignment. Member 2 does not implement greedy transcription or use open-ended STT as the clinical score.

### Alignment input

The GOP stage consumes Member 1's `AlignmentResult`, not raw alignment internals. Each aligned phoneme contains the expected token, start and end frame indices, start and end milliseconds, and segment confidence. The whole result contains an alignment confidence and an explicit valid or invalid status.

GOP is not evaluated when alignment is invalid, confidence is below the configured minimum, an expected phoneme is absent from the vocabulary, a segment is empty, or frame bounds exceed the probability matrix. These cases return an `unscorable` or `retry` result without a negative pronunciation judgement.

## GOP and Confidence Design

For an aligned segment with expected phoneme `p`, the baseline GOP evidence is calculated from the mean frame log posterior of `p` relative to the strongest non-blank competing phoneme:

```text
margin = mean(log P(p | frame)) - max_q!=p,blank(mean(log P(q | frame)))
gop = sigmoid(margin)
```

This baseline is deterministic, traceable, and independently testable. It is not represented as clinically calibrated until therapist-labelled calibration data exists.

Phoneme confidence combines acoustic separation and alignment confidence using configurable weights that sum to one. Category selection uses versioned thresholds:

- `pass`: score and confidence meet the pass thresholds;
- `coach`: score is below pass but evidence remains sufficiently confident;
- `retry`: evidence is confident and the score is below the coaching threshold;
- `unscorable`: capture, alignment, or acoustic confidence is insufficient.

Syllable scores are duration-weighted aggregates of their constituent phoneme scores. A syllable cannot receive a stronger category than an unscorable constituent permits. The response contains the underlying phoneme evidence so aggregation never hides the basis of the score.

The configuration carries `scoring_version`, thresholds, minimum alignment confidence, confidence weights, and aggregation method. Member 3 may map these categories to therapist-approved actions but does not alter Member 2's acoustic evidence.

## Assessment Output

The Member 2 result is a typed JSON-compatible structure:

```json
{
  "attempt_id": "ATT-00031",
  "status": "ok",
  "model_version": "ta-phoneme-ctc-1.0.0",
  "vocabulary_version": "ta-phonemes-1.0.0",
  "scoring_version": "gop-baseline-1.0.0",
  "phoneme_scores": [
    {
      "phoneme": "a",
      "gop": 0.9,
      "confidence": 0.92,
      "status": "pass"
    }
  ],
  "syllable_scores": [
    {
      "syllable": "அம்",
      "score": 0.86,
      "confidence": 0.88,
      "status": "pass"
    }
  ],
  "overall_confidence": 0.84,
  "reason": null
}
```

Failure responses contain an enumerated non-sensitive reason such as `model_integrity_failed`, `invalid_probability_contract`, `alignment_low_confidence`, or `phoneme_not_in_vocabulary`. They do not contain audio, transcript text beyond the known exercise token, embeddings, probability arrays, direct child identity, or diagnostic language.

## Model Development and Packaging

The offline modeling area contains reproducible entry points for:

- adapting or attaching a Tamil phoneme CTC head to an approved Tamil-aware encoder;
- exporting a frozen inference graph to ONNX with dynamic audio/frame axes;
- validating ONNX versus source-framework outputs on approved non-sensitive fixtures;
- generating SHA-256 manifests and model metadata;
- performing INT8 quantization as an experiment, not an automatic release step;
- comparing FP32 and INT8 phoneme probabilities, GOP results, model size, latency, and memory;
- generating a model card and benchmark manifest.

No trained production model will be fabricated. If the approved model, vocabulary, training data, or target device is unavailable, the command exits with a precise prerequisite error and leaves the contract/runtime/scoring test suite usable.

## Benchmark Design

Benchmarks record:

- model and manifest digests;
- vocabulary and scoring versions;
- device and execution provider;
- cold model-load time;
- median and P95 inference latency;
- model size;
- process peak memory where measurable;
- FP32-to-INT8 output and GOP degradation;
- fixture manifest digest and run timestamp.

Claims about Android memory, thermal behavior, battery, or end-to-end speech-to-avatar latency require the actual target device and are never inferred from laptop measurements. The repository can record laptop prototype evidence separately.

## Privacy and Safety

Member 2 code operates offline and has no HTTP client dependency. Safe logging records only model versions, tensor shapes, durations, status codes, and aggregate timing. Tests reject logging or serialization of waveforms, embeddings, log-probability matrices, transcripts, child names, voiceprints, or diagnostic outputs.

All error paths release runtime references and return neutral technical outcomes. The module never predicts ASD, diagnosis, treatment, or clinical improvement.

## Testing Strategy

Implementation follows red-green-refactor. Tests are divided by responsibility:

- contract tests for tensor shape, vocabulary, timing, versions, and JSON serialization;
- unit tests for log-probability validation, GOP competitor selection, confidence gates, thresholds, and syllable aggregation;
- integration tests using a tiny generated ONNX fixture, when ONNX Runtime is installed, to prove local model loading and deterministic output;
- integrity tests for missing or tampered manifests/models;
- privacy tests for safe logs and output schemas;
- export and quantization equivalence tests using synthetic or approved non-sensitive fixtures;
- benchmark-manifest tests for reproducible metadata and percentile calculation.

Every numerical expected value is hand-derived or generated from a fixed literal fixture independent of the implementation under test.

## Delivery Sequence

1. Repository structure, packaging, typed contracts, and privacy-safe defaults.
2. CTC vocabulary and probability validation.
3. GOP, confidence gating, categories, and syllable aggregation.
4. End-to-end Member 2 assessment service accepting Member 1 alignment input.
5. ONNX runtime, integrity manifest, and local inference integration tests.
6. Export, quantization, and benchmark tooling.
7. Model card, integration contract documentation, reproducibility instructions, and final Member 2 verification report.

Each slice remains independently testable. No Member 1 or Member 3 production module is implemented as part of this work.

## Acceptance Criteria

- Validated 16 kHz in-memory audio can be passed to a local model runtime without network access.
- The runtime produces deterministic frame-level log probabilities with explicit blank, timing, model, and vocabulary metadata.
- The forced-aligner input contract is documented and mechanically validated.
- GOP is calculated only from valid aligned segments and competing phoneme evidence.
- Phoneme and syllable results include confidence and `pass`, `coach`, `retry`, or `unscorable` status.
- Low-confidence or invalid alignment never produces a negative pronunciation judgement.
- Model files are locally packaged, integrity checked, and excluded from source control.
- FP32 and INT8 comparison tooling reports output/score degradation instead of assuming equivalence.
- Benchmarks report cold start, size, memory where measurable, and median/P95 latency with reproducible manifests.
- Tests, model card, contracts, and benchmark documentation cover all five Member 2 work packages without implementing another member's assigned scope.
