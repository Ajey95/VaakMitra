# Corpus, Inventory Review, and GPU Execution Design

**Date:** 2026-08-05  
**Status:** Approved strategy awaiting written-spec review  
**Owner:** Backend Member 2  
**Release ceiling before clinician sign-off and target-user evaluation:** engineering prototype

## 1. Decision

Materialize the complete IISc-MILE Tamil ASR corpus from OpenSLR 127 into ignored local storage,
verify and index it without committing speech or transcripts, generate a corpus-backed Tamil
phoneme candidate plus clinician review packet, and provide a pinned GPU runbook for staged
IndicConformer phoneme fine-tuning followed by compact-student distillation.

No automated process may change `expert_approved` or `production_ready` to true. A clinician or
Tamil speech expert reviews the candidate inventory and recording-label sample, records decisions
in the review packet, and supplies a separate signed approval manifest.

## 2. Source and storage

The primary corpus is OpenSLR resource 127, IISc-MILE Tamil ASR Corpus:

- canonical page: `https://www.openslr.org/127/`;
- archive: `mile_tamil_asr_corpus.tar.gz`;
- declared size: 13 GB;
- licence: CC BY 2.0;
- declared contents: approximately 150 hours from 531 speakers;
- audio contract: 16 kHz, 16-bit, mono PCM WAV;
- transcript contract: one UTF-8 Tamil text file per recording.

Private material is stored under
`modeling/artifacts/corpora/openslr-127/`, which is already excluded from Git. The directory holds
the compressed archive, extracted source tree, private record JSONL, speaker assignments, phoneme
lexicon, and voice-derived feature caches. Only aggregate counts, digests, review templates, and
non-sensitive runbooks may be committed.

The downloader is resumable and refuses an existing completed archive unless its stored digest and
size match. The source does not publish an authoritative archive checksum, so verification consists
of a locally computed SHA-256, the recorded source URL and retrieval time, successful gzip/tar
integrity checks, safe member paths, expected layout, complete audio/transcript pairing, and WAV
format validation. The report must call this a locally verified source snapshot, not a
publisher-supplied checksum.

## 3. Safe extraction and corpus validation

Before extraction, every tar member is inspected. Absolute paths, drive-qualified paths, parent
traversal, links escaping the extraction root, device nodes, and duplicate normalized destinations
are rejected. Extraction occurs only inside the resolved corpus artifact directory.

For every usable utterance, the materializer validates:

- paired WAV and transcript stems;
- finite positive duration;
- 16 kHz sample rate;
- one channel;
- 16-bit PCM encoding;
- non-empty UTF-8 Tamil transcript after NFC normalization;
- stable utterance and speaker identifiers derived from corpus metadata or layout;
- SHA-256 of audio bytes and normalized transcript text.

Invalid records are not silently corrected. They enter an aggregate rejection report with a stable
reason code. Paths, transcript text, speaker identifiers, and utterance identifiers remain in the
ignored private workspace and never enter committed reports.

## 4. Speaker-disjoint split policy

The official test partition is retained only if its speaker set is disjoint from the official
training partition. A validation set is selected deterministically from official-training speakers
using a versioned SHA-256 speaker assignment function.

If official train/test speaker overlap exists, all speakers are reassigned deterministically with
an 80/10/10 train/validation/test target. Assignment operates on speakers before phoneme generation,
feature extraction, augmentation, or batching. The frozen index rejects duplicate utterance IDs,
audio digests, transcript/audio pairing inconsistencies, or speaker overlap.

Committed aggregate evidence records split-level utterance, speaker, duration, and rejection counts;
archive, source-snapshot, private-index, assignment, and frozen-index SHA-256 values; and the exact
split-policy version.

## 5. Corpus-backed phoneme candidate

The inventory generator combines:

- pinned PHOIBLE Tamil inventories 1058, 1788, and 2611;
- pinned Epitran `tam-Taml` output;
- normalized words observed in the complete training-corpus transcripts;
- exercise vocabulary when supplied separately;
- explicit acoustic-only allophone decisions supplied through the review workflow.

Proposed defaults remain pending clinician approval:

- `<blank>` is vocabulary index zero;
- long vowels retain the IPA length marker, for example `/aː/`, as distinct acoustic targets;
- gemination is represented as repeated canonical consonant targets rather than an undeclared
  collapse into singleton consonants;
- diphthongs remain explicit when supported by the reviewed pronunciation source;
- allophones map only through individually declared, provenance-bearing rules;
- unresolved phones never map to a similar known phone and instead exclude the training sample or
  produce `unscorable` evidence;
- literary, colloquial, and loanword variants remain separate reviewable pronunciation entries.

The candidate contract contains core and extended tokens, per-token provenance, source conflicts,
observed coverage, unknown units, allophone mappings, and a stable digest. It always emits
`expert_approved=false`, `production_ready=false`, and
`evidence_scope=provisional_research_inventory`.

## 6. Clinician review package

The committed review package contains no recordings or complete corpus transcripts. It includes:

1. a Markdown guide explaining the acoustic-token policy and review procedure;
2. a CSV token inventory with source agreement, corpus frequency, example-word references,
   proposed class, reviewer decision, replacement, and notes columns;
3. a CSV pronunciation sample with anonymized sample reference, word, proposed phones, and fields
   for correct/substitution/insertion/deletion/vowel-length/gemination/unscorable decisions;
4. a JSON conflict and unknown-coverage report;
5. an approval-manifest template binding the archive, inventory, lexicon, review files, reviewer
   role, review date, decision, and SHA-256 values.

The approval importer accepts only a complete approved manifest whose hashes match the reviewed
artifacts. Importing approval produces a separate reviewed contract; it never edits or overwrites
the provisional source candidate. Reviewer names and contact information are not required; a role,
date, decision, and optional organization reference are sufficient.

## 7. IndicConformer transfer-learning runbook

The reference track uses the gated
`ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large` checkpoint at the pinned revision. The user
must accept the Hugging Face access conditions; tooling must not read, print, or bypass credentials.
The runbook pins the AI4Bharat NeMo revision, CUDA/PyTorch compatibility, package lock, container or
environment digest, corpus/index/vocabulary/config hashes, and hardware report.

Training proceeds in three stages:

1. replace or bypass the text decoder, attach the reviewed phoneme CTC head, freeze the encoder,
   and train the head at learning rate `1e-3`;
2. unfreeze the top four encoder blocks, use head learning rate `1e-4` and encoder learning rate
   `1e-5`;
3. unfreeze the full encoder only after validation phone error improves, using head learning rate
   `5e-5` and encoder learning rate `1e-6`.

Every stage uses deterministic seeds, BF16 mixed precision where supported, gradient clipping at
1.0, gradient accumulation sized to GPU memory, resume-safe checkpoints, early stopping on
speaker-disjoint validation phone error, and finite-loss/gradient aborts. The frozen test split is
evaluated once after checkpoint selection. Reports include micro/macro PER, exact phone-sequence
accuracy, per-phone confusion, robustness degradation, calibration inputs, and failure analysis.

## 8. Teacher-to-student distillation runbook

The selected reference checkpoint produces local, hash-bound hidden representations. Each feature
cache binds teacher revision, teacher checkpoint digest, audio digest, frame count, feature
dimension, and preprocessing configuration. Caches remain ignored and are removed only after the
experiment's immutable evidence package is complete.

Both compact candidates train on identical speaker-disjoint manifests:

- compact Conformer CTC;
- convolutional BiGRU CTC.

The objective combines supervised phoneme CTC, masked Smooth-L1 projected representation loss,
normalized relational frame-similarity loss, and an ablated optional sequence-consistency term.
Text-posterior KL is prohibited because the teacher ASR tokens and phoneme vocabulary are not
compatible label spaces.

Selection compares adult-Tamil PER, controlled-confusion AUROC/FAR/ECE, robustness, parameter count,
FP32/INT8 size, PyTorch/ONNX/INT8 parity, aligned GOP change, and physical-device evidence when
available. No student is selected merely because it is smaller.

## 9. Promotion gates

The reference continuation target is adult-Tamil PER at or below 0.20 and statistically significant
improvement over the historical proxy. The student additionally requires:

- compressed size at or below 50 MB;
- absolute INT8 PER degradation at or below 0.01;
- median absolute aligned GOP change at or below 0.03;
- controlled-confusion AUROC at or above 0.90;
- proxy false-accept rate at or below 0.05;
- expected calibration error at or below 0.05;
- no severe-corruption confident-decision violation;
- physical Android model-only P95 at or below 500 ms before device promotion.

Missing evidence is `not_measured`, never a pass. Clinician inventory approval does not imply child
accuracy, therapist calibration, or clinical effectiveness.

## 10. Failure and recovery behavior

- Network interruption leaves a resumable partial archive.
- Archive/source mismatch preserves the suspect file under a quarantine name and blocks extraction.
- Unsafe tar members block extraction before any member is written.
- Audio/transcript or WAV-format failures are counted and excluded with stable reason codes.
- Unknown phonemes block affected training examples until reviewed.
- Gated-model refusal reports `model_access_not_authorized`.
- Missing NeMo or CUDA reports the existing stable preflight code.
- Non-finite training aborts and preserves only non-sensitive diagnostics and the last safe
  checkpoint.
- Digest mismatch blocks resume, feature-cache loading, export, inference, and approval import.

## 11. Verification

Implementation follows test-first development. Automated coverage must prove downloader state
transitions without downloading the real archive, tar path-safety rules, pairing and WAV validation,
speaker-disjoint deterministic assignments, private-versus-aggregate serialization, inventory
review completeness, immutable approval import, GPU configuration validation, stage promotion, and
student comparison gates.

The real materialization run must record the archive size and SHA-256, integrity-check result,
aggregate corpus counts, audio hours, rejection counts, split counts, inventory coverage and
unknowns. Repository verification includes the complete test suite, Ruff, strict mypy, package
build, `git diff --check`, tracked secret/large-file scans, and proof that recordings, transcripts,
private identifiers, checkpoints, feature caches, and model weights remain untracked.

