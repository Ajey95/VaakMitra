# Local Gemma 4 E2B adult sound benchmark — 14 November 2026

**Result: the tested direct-phone-transcription and exact-corroboration approach did not improve omission/substitution detection. Do not activate it in the app.** The local GPU/audio runtime worked; reliable phonetic assessment did not follow from that capability. This result does not evaluate every possible Gemma prompting or fine-tuning method.

## Matched development comparison

Existing public adult data:132 MSWC keyword clips and27 OpenSLR65 complete utterances,159 unique sources. The same 565 reference comparisons comprise 159 own-target controls and 406 lexical sound contrasts. These are provisional word-derived engineering references, not independently annotated natural pronunciation errors. No child/private recordings were used.

| System | Omission contrasts identified /158 | Substitution contrasts identified /248 | Total /406 | Own-target alerts /159 | Wrong sound attributions |
|---|---:|---:|---:|---:|---:|
| Retained phoneme assessor, threshold0.99 |10|34|44|0|0|
| Gemma direct observed phones |0|0|0|0|0|
| Exact Gemma corroboration, every predeclared cutoff0.5–0.99 |0|0|0|0|0|

Gemma returned explicit uncertainty on 138/159 sources. Its 21 nonempty phone outputs all came from complete utterances: all 132 keyword clips and 6/27 complete utterances were uncertain. The 21 outputs were not independently verified actual-sound transcripts and did not yield a unique supported one-sound reference comparison. All 565 Gemma-only comparisons abstained. Exact full-sequence corroboration rejected every positive acoustic proposal at all 7 cutoffs. Zero false alerts in this situation reflects absence of positive corrections, not 100% precision or clinical accuracy.

Keyword subgroup: phoneme-only 23/342 contrasts (2/129 omission, 21/213 substitution); complete-source subgroup 21/64 (8/29 omission, 13/35 substitution). Gemma and corroborated positive detections were 0 in both groups. Full scope and keyword edge/interior metrics remain in the diagnostic JSON; unsupported and uncertain rows stay in the denominators.

## Frozen method and failed gate

Gemma Q4_0 language weights plus matching Q8_0 audio projector, pinned repository revision`2a8538c2e2d4687953a86c422c7c623cfd022880`; CUDA12.4 llama runtime`b12377`. All 4 download digests verified. Assets remain in`D:/VaakMitraGemmaResearch/20261114` (4,109,697,329download bytes plus extracted runtimes).

The phoneme side used the retained acoustic body`ff41636b23a41baa0ebb08e59f00fe684c9a054e40a9c41eb685542b5f5020cf` and its previously frozen local-lattice assessor. The separate raw LoRA preview candidate was outside this comparison. Acoustic weights/raw decoding were not changed.

The target-blind Gemma request contained audio and the permitted canonical IPA units only: no intended word, expected sequence, candidate diagnosis, source ID or transcript. Unknown/invalid/incomplete outputs abstained. No spelling transcription was converted into purported actual phones. Independent phone observations were compared with the same frozen references; corroboration required exact agreement with the acoustic proposal's alternative full sequence and its existing body/registry/confidence checks.

Initial structural controls: 2 speech sources, repeats, 2 duration-matched silences and 2 equal-duration speech variants (8 requests total). Both silences returned valid uncertainty; speech responses were repeatable, but one speech source abstained. **The predeclared structural smoke gate FAILED.** Its original report remains immutable.

SSOT3.3.77 expressly permits completing the same exposed development panel as descriptive diagnostics after that failure. Version 4 binds the parent version 3 freeze, preserved runner, unchanged source/model/prompt/references and 8 reused responses. Only 157 remaining source observations were queried. No winning cutoff was selected. Eligibility, mobile, child and clinical flags remain false. No 96 keyword + 10 complete heldout audit or old 400/173/1665 panel was inferred, and no prompt/model/threshold-grid tuning followed these results.

## Runtime observations and privacy

- RTX 4060 Laptop GPU, 8188 MiB reported capacity. Largest whole-device memory snapshot during the full diagnostic: 2401 MiB; sampled memory is not an exact process peak. Windows process working-set snapshots are separately retained; internal RAM telemetry was unavailable.
- 159 source requests total 87.086 seconds; median 0.453 seconds per source, including immediate resource telemetry. This excludes model loading, archive access/decoding, extraction, hashing and control requests. It is not phone latency.
- Audio decoded/resampled locally and transported as mono 16 kHz PCM16 in memory. Rounding/clipping from the baseline float waveform is disclosed; its independent recognition effect was not measured. Original files, duration and pauses were preserved.
- Before transmitting any HTTP body, the established loopback TCP connection was verified to belong to the launched GPU process. Per-run authentication, offline/local-file model operation and a client without proxy/redirect support were used. Nonces were redacted from saved launch metadata. No audio/base64 requests were saved, no cloud fallback was configured and no recording was sent to an external LLM. This is implementation/runtime evidence, not a full forensic packet-capture certification.
- Atomic source checkpoints preserve all 159 outcomes and 6 control responses. Resumption is bound to exact protocol/source/model identities; a failed source remains neutral rather than disappearing.
- 94 relevant tests passed, 0 failures/errors/skips, including a real Windows socket-owner test proving that a mismatched PID receives no request body. One fresh source review and one material regression-backed fix pass were completed; startup path plumbing was subsequently regression-tested before audio inference. No repeat review.
- All 541 Android files in the preceding delivery proof matched their hashes. No APK was built/installed, no phone action occurred, and avatars/session UX/rewards/capture were unchanged.

## Disposition

Keep this Gemma detector inactive. The benchmark establishes that the pinned model can execute locally with audio on this laptop; it does not establish dependable Tamil phone transcription or sound corrections. The strict exact-sequence fusion can also discard partial agreement, so this is a finding about the tested approach.

An offline mobile architecture remains technically possible, but this combination is not ready for reliable correction deployment. Android runtime/audio support, model format, memory, latency, cancellation and independent pronunciation-error validity need their own successful evidence. Voice guidance can continue through the existing offline Tamil system without asserting unverified sound errors.

## Evidence locations

Private research root:`D:/VaakMitra-Integrated-Backend-Lab/.superpowers/sdd/2026-11-14-local-gemma-adult`.

- `diagnostic-development-result.json`: all metrics,7fixed cutoffs, scope/edge/interior breakdowns, source timings and sampled GPU memory.
- `diagnostic-matched-outputs.json`: 565 compact case outputs, indexed to immutable original evidence by SHA256.
- `diagnostic-observations/`: 159 source and6control records, including parent provenance for reused outputs.
- `benchmark-result.json`and`smoke-results.json`: preserved original failure.
- `benchmark-protocol-v4.json`and`freeze-v4.json`: actual descriptive diagnostic freeze; original protocols/freezes/sources retained.
- `download-manifest.json`,runtime proofs,`app-preservation-proof.json`,`diagnostic-backend-verification.xml`: identities and validation.

Primary implementation provenance: [Gemma model card](https://huggingface.co/google/gemma-4-E2B-it), [pinned GGUF repository](https://huggingface.co/ggml-org/gemma-4-E2B-it-GGUF/tree/2a8538c2e2d4687953a86c422c7c623cfd022880), [llama runtime release](https://github.com/ggml-org/llama.cpp/releases/tag/b12377). Vendor capability claims do not substitute for the measurements above.
