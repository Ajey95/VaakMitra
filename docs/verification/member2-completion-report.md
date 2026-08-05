# Member 2 Technical-Prototype Completion Report

## Decision and scope

This report audits Backend Member 2 against work packages M2.1-M2.5 after the team confirmed that
therapist-labelled Tamil child recordings and the target Android tablet are unavailable. The
approved fallback uses licensed adult Tamil data and development-laptop evidence. It does not relax
the prohibition on clinical, child-validity, or tablet-performance claims.

## Outcome

The approved Member 2 engineering fallback is implemented end to end: local inference contracts,
CTC output validation, GOP/confidence scoring, privacy gates, immutable corpus provenance,
speaker-disjoint proxy preparation, CPU training, ONNX export, INT8 conversion, evaluation,
benchmarking, hash-linked release evidence, mocked adjacent-member contract execution, provisional
IPA inventory generation, research-source preflight, safe teacher-feature packaging, and static
mobile compatibility auditing.

The result is correctly gated as a `technical_prototype`. It is not an accurate production scorer:
the bounded adult-proxy model has a test phone-unit error rate of `0.9819819819819819` and exact
sequence accuracy of `0.0`.

## Work-package audit

### M2.1 Tamil acoustic-model runtime

Verified engineering evidence:

- local, HTTP-free `OnnxAcousticModelRuntime` with SHA-256 verification before session creation;
- explicit ONNX Runtime execution provider and safe failure behavior;
- raw mono 16 kHz waveform input and frame-level logits/log-probability output;
- trained adult-proxy FP32 and INT8 model artifacts generated locally and excluded from Git;
- deterministic synthetic and trained-proxy runtime integration tests.

Acceptance status: engineering fallback complete. Model accuracy is not production-acceptable.

### M2.2 Phoneme-level CTC output head

Verified engineering evidence:

- versioned blank/vocabulary/tensor/frame-timing contract for Member 1;
- standard CTC collapse, edit distance, micro/macro phone-unit error rate, exact accuracy, and
  unscorable-rate evaluation;
- reproducible raw-waveform Conv-BiGRU CTC training and dynamic-sample ONNX export;
- immutable proxy vocabulary and model manifests;
- deterministic Epitran-backed provisional Tamil IPA/token manifest generation with NFC
  normalization, duplicate rejection, and explicit non-approval flags.

Acceptance status: training/output path complete. The current 32 units are explicitly
`unicode_codepoint_proxy_not_expert_phoneme_inventory`, not the final Tamil-expert-approved
inventory. The Epitran output is a preparation aid and also remains provisional until Tamil-expert
review.

### M2.3 GOP and confidence scoring

Verified engineering evidence:

- literal expected-versus-competitor GOP tests;
- confidence combination, pass/coach/retry/unscorable gates, and syllable aggregation;
- neutral outcomes for invalid, weak, or mismatched evidence;
- proxy threshold calibration with false-accept ceilings, deterministic ties, calibration error,
  and unscorable accounting;
- mechanical rejection of therapist-calibrated labelling without target-user evidence.

Acceptance status: scoring/calibration software complete. Real proxy-model GOP calibration remains
unavailable until Member 1 supplies validated alignments; therapist calibration remains unavailable
without therapist-labelled target-user ratings.

### M2.4 Model export and edge optimization

Verified trained-proxy measurements:

- FP32 ONNX size: `70,757` bytes;
- dynamic INT8 ONNX size: `48,679` bytes (`0.687974` of FP32);
- maximum posterior delta: `0.00008893385529518127`;
- GOP delta: unavailable for the real model because no Member 1 validated alignment exists;
- INT8 cold load: `223.6853 ms` on the development laptop;
- INT8 inference median/P95: `0.78375 / 2.9517 ms` across 30 measured runs;
- peak process RSS: `68,829,184` bytes;
- official static ONNX Runtime mobile audit: NNAPI supports `8/51` nodes as-is in `5` partitions;
- fixed-shape analysis: NNAPI supports `37/51` nodes in `10` partitions but is still rated `NO`;
- recorded provider recommendation: `CPUExecutionProvider`.

Acceptance status: export, quantization, comparison, and reproducible laptop benchmark complete.
Static operator compatibility is now recorded, but Android latency, memory, battery, and thermal
acceptance remain unavailable without the actual tablet and cannot be inferred from these numbers.

### M2.5 Testing, documentation, and review

Verified repository evidence:

- `184` automated tests pass;
- Ruff passes across backend, tests, modeling, and benchmarks;
- strict mypy passes across `61` source files;
- sdist and wheel build successfully;
- model card, architecture, contracts, training instructions, manifests, and reports are updated;
- real audio, speaker-level indices, checkpoints, ONNX weights, waveforms, and probability matrices
  remain outside Git.

Acceptance status: implementation, automated tests, integration evidence, and documentation are
complete. The PRD-required teammate cross-review cannot be self-produced and remains a team action.

## Proxy-data provenance

The recorded public source is `asishbala/tamil-tts-dataset` at immutable revision
`1d6a78e02c6c21d8da30eb57dd4dc02b4ed765f5`, declared `CC0-1.0`.

The source has 46,368 records and 22 speakers. Its original train and validation CSVs share all 18
development speakers. The checked-in preparation tool therefore derives new disjoint splits:

- train: 26,666 records / 14 speakers;
- validation: 11,940 records / 4 speakers;
- test: 7,762 records / 4 speakers.

The bounded recorded training run uses 42/8/8 utterances while retaining all 14/4/4 speaker groups.

## Alternative preparation and mocked dependencies

- Test-only Member 1 creates deterministic balanced half-open frame alignments and returns neutral
  invalid evidence when allocation is impossible.
- Test-only Member 3 maps validated Member 2 statuses to deterministic actions without persistence,
  synchronization, or therapy-policy claims.
- The mocked three-member runner records hashes and contract outcomes without audio, embeddings,
  transcripts, probability matrices, or child identity.
- `tamil_research_sources.json` pins IndicVoices and Vistaar revisions. IndicVoices is explicitly
  adult-only, terms-gated, and unavailable for automatic download; Vistaar remains discovery-only
  until each underlying dataset licence is reviewed.
- The pinned IndicConformer teacher configuration states that its ASR head does not provide direct
  phoneme posteriors. Local feature caches require float32 finite 2-D tensors, model/audio/feature
  hashes, non-overwrite behavior, and local-only voice-derived storage.

These mechanisms unblock Member 2 engineering while real teammate components and target evidence
are absent. They do not substitute for those acceptance inputs.

## Evidence index

- `modeling/manifests/tamil-tts-public-source-audit.json`: licence, revision, hashes, leakage audit,
  and derived aggregate split counts;
- `benchmarks/reports/proxy-training-adult-tamil.json`: configuration, losses, validation/test
  phone-unit metrics, model digest, and limitations;
- `benchmarks/reports/proxy-fp32-vs-int8.json`: trained-proxy optimization comparison;
- `benchmarks/reports/proxy-int8-development-laptop.json`: trained-proxy laptop benchmark;
- `benchmarks/reports/proxy-calibration-status.json`: explicit unavailable alignment/calibration
  evidence;
- `benchmarks/reports/member2-proxy-trained-evidence.json`: final hash-linked evidence bundle;
- `benchmarks/reports/member2-mocked-three-member-evidence.json`: mock-only adjacent-member contract
  execution;
- `modeling/configs/tamil_research_sources.json`: pinned fail-closed research-source preflight;
- `modeling/configs/indicconformer_teacher.json`: pinned research-only teacher boundary;
- `benchmarks/reports/proxy-int8-mobile-usability.json`: static NNAPI support and CPU-provider
  recommendation.

## Remaining external acceptance gates

These items cannot be completed by code or proxy data and must not be represented as done:

1. Tamil-expert approval of the final phoneme inventory and length/gemination conventions.
2. A materially better trained model that meets a predeclared proxy benchmark before child testing.
3. Member 1 forced-alignment integration and aligned FP32/INT8 GOP comparison.
4. Ethics-approved therapist-labelled Tamil target-user evaluation and calibration.
5. Actual Android-tablet latency, memory, battery, and thermal measurements.
6. Cross-review by Members 1 and 3.

Until those gates exist, the release label must remain `technical_prototype` and weak evidence must
continue to return `unscorable` or retry rather than a negative pronunciation judgement.

## Verification commands

```powershell
& .\.venv\Scripts\python.exe -m pytest backend\tests -q
& .\.venv\Scripts\python.exe -m ruff check backend\src backend\tests modeling benchmarks
& .\.venv\Scripts\python.exe -m mypy backend\src modeling benchmarks
& .\.venv\Scripts\python.exe -m build backend
git diff --check
```
