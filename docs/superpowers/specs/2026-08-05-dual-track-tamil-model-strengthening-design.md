# Dual-Track Tamil Model Strengthening Design

**Date:** 2026-08-05  
**Status:** Proposed for implementation after written-spec review  
**Owner:** Backend Member 2  
**Release ceiling without target-user evidence:** engineering prototype

## 1. Decision

Implement both model strategies against one shared evidence contract:

1. **Track A (the user's Strategy 2, full reference):** fine-tune the AI4Bharat Tamil
   IndicConformer encoder with a new
   Tamil phoneme CTC head.
2. **Track B (the user's Strategy 1, hybrid edge pipeline):** use the successful full reference
   model as a teacher and distill its acoustic representations into a compact Tamil phoneme CTC
   model suitable for ONNX Runtime on Android.

The full reference track is implemented first because it supplies the teacher representations and
an accuracy ceiling for the student. Both tracks are evaluated on identical frozen manifests,
phoneme targets, metrics, robustness conditions, and scoring fixtures.

Completing both tracks means producing reproducible training code, pinned configurations,
checkpoints, evaluation reports, export attempts, calibration evidence, and a comparison report.
It does not mean declaring clinical validity, Tamil-ASD accuracy, therapist agreement, or final
target-tablet acceptance without those external inputs.

## 2. Architecture invariant

The PRD's two-phase local scoring architecture remains unchanged:

```text
Member 1 validated mono 16 kHz audio
                |
                v
Member 2 Tamil encoder + phoneme CTC head
                |
                v
AcousticOutput [frames, phoneme vocabulary] log probabilities
                |
                v
Member 1 forced alignment against the known expected phonemes
                |
                v
Member 2 GOP + confidence + syllable aggregation
                |
                v
Member 3 therapist-constrained response action
```

Neither track adds open-ended transcription to the scoring path. IndicConformer's text-ASR
posteriors are not reinterpreted as phoneme posteriors. Audio, hidden features, probability
matrices, and transcripts remain local and outside persistence or synchronization payloads.

## 3. Shared Tamil phoneme contract

Member 2 will generate a versioned **candidate acoustic vocabulary** for model training and return
its conflict report to Member 1. Member 1 retains ownership of the production pronunciation
dictionary, G2P rules, syllabification, and therapist/expert overrides.

The candidate vocabulary is built from:

- the three Tamil inventories recorded by PHOIBLE;
- Epitran `tam-Taml` and `tam-Taml-red` outputs;
- the exercise vocabulary and training-corpus transcripts;
- explicit Tamil vowel-length and gemination markers;
- explicit literary, colloquial, loanword, and allophone policies.

The generated package contains:

- a stable blank token and ordered canonical phoneme list;
- a core-versus-extended inventory classification;
- allophone-to-canonical mappings used only for acoustic scoring;
- pronunciation variants per normalized word;
- provenance for every segment and rule;
- a machine-readable conflict ledger for source disagreements;
- coverage and unknown-token reports for every data split;
- `expert_approved=false` and `production_ready=false` until external sign-off.

Unknown or unresolved phones never map silently to a known phone. They make the sample unscorable
or exclude it from training with an explicit reason.

## 4. Shared data program

### 4.1 Primary adult Tamil data

Use the IISc-MILE Tamil ASR corpus as the primary expansion beyond the current 42-utterance proxy:
approximately 150 hours, 531 speakers, 16 kHz mono PCM, Tamil transcripts, and CC BY 2.0.

Additional Vistaar-linked Tamil datasets may be added only after a dataset-specific audit confirms:

- canonical source and immutable revision;
- licence and redistribution/training permissions;
- speaker identifiers or a defensible participant split;
- transcript provenance and normalization;
- age/population scope;
- absence of train/validation/test speaker overlap.

The Vistaar repository licence must not be treated as licensing every underlying dataset.

### 4.2 Default child-data policy

No child audio is required for these two implementation tracks. The default design uses no public
general-child corpus either. Child-like acoustic transformations provide stress evidence only.

If the user later explicitly permits a licensed general-child corpus, it may be used only for
self-supervised encoder adaptation or a separately reported ablation. It must not be labelled Tamil
or ASD evaluation and must never enter the frozen adult-Tamil test split.

### 4.3 Split and leakage controls

- Split by speaker before feature extraction, augmentation, pseudo-labelling, or batching.
- Freeze one adult-Tamil test manifest before model selection.
- Keep calibration records separate from the final adult test manifest.
- Hash source revisions, manifests, normalized transcripts, vocabulary, and configurations.
- Reject overlapping audio digests, speaker IDs, or normalized utterance IDs across splits.
- Keep waveform and voice-derived caches under ignored local artifact directories.

## 5. Track A (Strategy 2): full IndicConformer phoneme fine-tuning

### 5.1 Upstream model

Use the pinned gated model:

`ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large`

The current research record identifies a roughly 120M-parameter, 17-block, 512-dimension Tamil
Conformer with hybrid CTC/RNNT text-ASR decoders. Its model card is MIT-licensed, but the files are
gated. The user must accept the upstream access conditions; the implementation will not automate
acceptance or bypass access control.

### 5.2 Model conversion

- Load the frozen upstream encoder through the pinned AI4Bharat NeMo revision.
- Remove or bypass the text-ASR decoder for the pronunciation model.
- Attach a randomly initialized linear phoneme CTC head matching the shared candidate vocabulary.
- Preserve blank index, frame shift, input normalization, and encoder subsampling metadata.
- Do not copy text-token logits into phoneme targets.

### 5.3 Training schedule

Use staged fine-tuning to reduce catastrophic forgetting:

1. Train only the new phoneme head with the encoder frozen.
2. Unfreeze the top encoder blocks and train with a lower encoder learning rate.
3. Run an optional full-encoder low-learning-rate phase only if validation phone error improves.
4. Select the checkpoint using speaker-disjoint validation phone error plus robustness metrics, not
   training loss alone.

Training uses mixed precision, gradient accumulation, gradient clipping, deterministic seeds, and
resume-safe checkpoints. A CPU smoke profile validates data and shapes; the complete run requires a
CUDA-capable job because the current workstation has no NVIDIA GPU.

### 5.4 Full-track deliverables

- pinned environment and model-access preflight;
- phoneme-head model definition and checkpoint converter;
- staged training CLI and resumable configuration;
- speaker-disjoint evaluation report;
- robustness and controlled-confusion report;
- FP32 export attempt and operator report;
- model card and hash-linked evidence manifest;
- explicit deployability outcome rather than a forced mobile claim.

The full model is the accuracy/reference candidate. It is not required to meet the edge size gate.

## 6. Track B (Strategy 1): compact teacher-distilled edge model

### 6.1 Student candidates

Compare at least two compact streaming-friendly encoders under the same parameter budget:

- a small Conformer CTC student;
- an improved convolutional-BiGRU CTC student used as the lightweight baseline.

The comparison selects architecture and size from evidence. The current 16,112-parameter proxy is
retained only as a historical baseline, not as the final student.

### 6.2 Distillation objectives

Train the student with a weighted combination of:

- supervised phoneme CTC loss from transcript-derived phoneme sequences;
- masked-frame representation loss against projected teacher hidden states;
- relational loss that preserves pairwise frame similarity;
- optional sequence-level consistency after CTC collapse.

Direct KL divergence against IndicConformer's text-ASR posterior vocabulary is prohibited. Teacher
features are extracted locally, stored only in hash-linked local caches, and deleted according to
the voice-derived artifact policy after the experiment is frozen.

### 6.3 Edge optimization

- Export the selected student to dynamic-sample FP32 ONNX.
- Apply dynamic and, where operator support allows, static INT8 quantization.
- Compare phone error, controlled-confusion scoring, GOP output, and confidence before promotion.
- Produce ONNX Runtime CPU and NNAPI operator audits.
- Generate an Android package manifest binding model, vocabulary, normalization, and hashes.

### 6.4 Student-track deliverables

- two student configurations and parameter reports;
- reproducible teacher-feature extraction;
- distillation training and ablation reports;
- frozen FP32 and INT8 model manifests;
- parity, quantization, and static mobile reports;
- representative physical-device benchmark when an APK harness is available;
- a comparison explaining why the selected student won.

## 7. Engineering calibration without therapist labels

The project will implement **proxy calibration**, never therapist calibration, from clean adult
Tamil speech plus controlled expected-sequence corruption.

### 7.1 Positive and controlled-negative evidence

- Positive: a clean recording paired with its expected phoneme sequence.
- Substitution negative: replace one expected phoneme with its nearest feature-space competitor.
- Length negative: swap short and long vowel targets.
- Gemination negative: insert or delete a repeated consonant target.
- Sequence negative: insert, delete, or transpose a target phone.
- Quality negative: add noise, clipping, reverberation, long pauses, repetitions, and rate changes.

Changing the expected sequence creates known acoustic-target mismatches without pretending that a
synthetic voice is a clinically realistic mispronunciation.

### 7.2 Confidence ensemble

Combine:

- expected-versus-competitor GOP margin;
- alignment confidence from Member 1;
- normalized CTC posterior entropy;
- top-one versus top-two posterior margin;
- blank dominance and segment duration checks;
- agreement between forced-aligned and alignment-free scoring variants;
- disagreement between full and student models during evaluation.

Threshold fitting is phone-specific where sample support is adequate and pooled by phonological
class otherwise. The calibration report includes false accept/reject rates, AUROC, Brier score,
expected calibration error, bootstrap intervals, and unscorable rate.

Categories remain `proxy_pass`, `proxy_coach`, `retry`, and `unscorable` in research evidence.
Production `pass` and `coach` thresholds remain externally gated by therapist labels.

## 8. Child-like robustness program

Without child recordings, the system reports transformation robustness rather than child-domain
accuracy. The frozen stress matrix includes:

- pitch and formant transformations sampled from documented child-speech ranges;
- speaking-rate changes and long intra-word pauses;
- repetitions, false starts, and leading/trailing silence;
- room impulse responses and background noise at multiple SNRs;
- gain reduction, saturation, and clipping;
- resampling and microphone-bandwidth variation;
- optional VTLN as a controlled on/off ablation.

Metamorphic expectations are explicit: moderate transformations should preserve the phone sequence
and relative score ordering, while severe corruption should increase `unscorable` rather than
produce confident negative feedback.

## 9. Evaluation and promotion gates

All gates are computed separately for the full model and each student candidate.

### 9.1 Model quality

- Primary metric: speaker-disjoint adult-Tamil phone error rate.
- Strong engineering target: phone error rate at or below `0.20` on the frozen adult test set.
- Minimum continuation gate: statistically significant improvement over the current `0.98198`
  proxy and over the non-distilled student baseline.
- Controlled-confusion AUROC target: at least `0.90`.
- Proxy false-accept target: at most `0.05` at the selected conservative threshold.
- Expected calibration error target: at most `0.05` on the proxy calibration set.

Failure to meet a gate produces an explicit failed experiment and error analysis; it does not get
relabelled as successful.

### 9.2 Robustness

- Report absolute and relative phone-error degradation for every transformation.
- Report score-order inversions and confidence changes.
- Severe-condition failures must prefer `unscorable` over confident pass/coach/retry.
- VTLN is retained only if its predeclared ablation improves the aggregate robustness objective.

### 9.3 Quantization

- INT8 phone-error degradation must be at most one absolute percentage point.
- Median absolute phoneme-GOP change must be at most `0.03` on aligned fixtures.
- Model and vocabulary hashes must match before runtime creation.

### 9.4 Edge evidence

For the student candidate:

- compressed model target: at most 50 MB;
- model-only P95 inference target: at most 500 ms on at least one representative physical Android
  device using the declared execution provider;
- record cold load, median/P95, peak memory, provider, device fingerprint, repetitions, and thermal
  status where the service exposes it;
- run with only synthetic or separately approved non-sensitive audio fixtures;
- verify offline execution and absence of network access from the scoring runtime.

These are representative-device gates. Exact final-tablet acceptance remains open until that device
class is named and measured.

## 10. Physical-device alternative

Use AWS Device Farm physical Android tablets when tablet form factor is required, or Firebase Test
Lab physical Android devices for build-managed CI coverage. The Android benchmark harness contains:

- integrity-checked model loading;
- cold/warm inference loops;
- AndroidX benchmark instrumentation;
- approved synthetic PCM fixtures bundled with the test APK;
- output collection for JSON metrics and traces;
- an offline/network-denial assertion.

Emulator runs remain functional checks and are never reported as physical-device performance.

## 11. Comparison and release decision

The final comparison report includes:

- full IndicConformer phoneme model;
- distilled Conformer student;
- improved Conv-BiGRU baseline;
- current tiny proxy as a historical reference.

Compare phone error, calibration, controlled-confusion detection, transformation robustness, model
size, exportability, operator support, latency, and peak memory. The full model establishes the
reference ceiling; the student is promoted only if it satisfies the edge gates with an acceptable
quality gap. It is valid for both tracks to fail a promotion gate while their implementation and
evidence remain complete.

## 12. Error handling and safety

- Missing gated access returns `model_access_not_authorized` without printing credentials.
- Missing CUDA for a full run returns `gpu_required_for_full_training` after CPU smoke validation.
- Dataset licence or revision uncertainty blocks materialization.
- Unknown phonemes block the affected sample or make it unscorable.
- Non-finite loss, features, logits, or probabilities abort the run and preserve a diagnostic
  checkpoint without voice data.
- Model/vocabulary/config digest mismatch blocks inference.
- Weak acoustic, alignment, or calibration evidence produces `unscorable`.
- Logs reject audio, hidden features, full probability matrices, transcripts, child identity, and
  diagnostic claims.

## 13. Testing strategy

Implementation follows red-green-refactor. Required automated coverage includes:

- cross-source inventory consensus and conflict handling;
- corpus split leakage and digest validation;
- gated-access and CUDA preflight behavior;
- phoneme-head dimensions, blank handling, loss finiteness, and freeze schedules;
- teacher/student frame projection and masked distillation losses;
- checkpoint resume determinism;
- controlled phoneme substitutions, length, and gemination errors;
- confidence-ensemble and proxy-calibration metrics;
- augmentation determinism and metamorphic outcome rules;
- ONNX export, FP32/INT8 parity, integrity, and provider behavior;
- Android report parsing and privacy-field rejection;
- regression coverage for the existing two-phase Member 2 pipeline.

## 14. Resource and access prerequisites

Current environment evidence:

- approximately 745 GB free on the workspace drive;
- PyTorch 2.11 CPU installed;
- no NVIDIA GPU or CUDA device detected;
- a Hugging Face token file exists, but access to the gated IndicConformer file is not yet confirmed.

Therefore:

- local work can complete source audit, data preparation, vocabulary generation, unit/integration
  tests, CPU smoke training, evaluation tooling, student prototypes, export, and report generation;
- the complete full-model fine-tuning run requires a CUDA GPU job or access to another CUDA machine;
- the user must accept any gated upstream model conditions in their own account;
- cloud/device services and any paid compute require explicit user authorization before use.

## 15. Completion criteria

The dual-track implementation is complete when:

1. Both tracks share one immutable Tamil phoneme/data/evaluation contract.
2. The full IndicConformer phoneme model has a reproducible completed training run and frozen report.
3. The student has completed teacher distillation, FP32 export, INT8 evaluation, and comparison.
4. Proxy calibration and child-like robustness evidence is reported for both tracks.
5. Representative physical Android evidence exists for the edge student, or a precise external
   service-access blocker is recorded without substituting emulator numbers.
6. Every promotion gate is reported as pass or fail with no missing metric disguised as success.
7. Existing tests, new tests, Ruff, strict mypy, package build, CLI help, privacy checks, and
   repository cleanliness all pass.
8. Documentation continues to defer therapist calibration, Tamil-ASD child accuracy, and exact
   target-tablet acceptance.

## 16. Explicit non-goals

- Replacing Member 1's production G2P, pronunciation dictionary, or forced aligner.
- Treating IndicConformer text transcription as pronunciation scoring.
- Uploading child audio or voice-derived representations.
- Accepting gated model/dataset terms on the user's behalf.
- Claiming that adult Tamil, synthetic errors, or acoustic transformations establish child or
  clinical validity.
- Forcing a full 120M-parameter model into the Android release if it fails size, operator, or
  latency evidence.
