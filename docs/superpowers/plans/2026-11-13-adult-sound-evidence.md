# Adult Sound Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Owner explicitly requested continuous implementation using laptop GPU and synthetic audio. Implement inline with one scoped final review.

**Goal:** Improve adult sound-difference evidence on controlled synthetic/public probes, and wire qualified evidence into existing neutral voice guidance.
**Architecture:** Bounded CTC likelihood comparison with native-compound canonicalization, separated from free decoding. Local Tamil VITS generates known designed contrasts; no audio goes toLLM. Existing offline AndroidTTS supplies coaching.
**Tech Stack:** Existing numpy/scipy/PyTorch CUDA, pinned local VITS, Kotlin/Compose. No new cloud/API.
**Spec:** ../specs/2026-11-13-adult-sound-evidence-design.md

## Global Constraints
SSOT3.3.63 DEC072/PHN013/COA002. No child audio/1665cohort, training/reference leakage, post-test threshold tuning, raw decoded-phone replacement, externalLLM, child scoring or avatar/session changes. All uncertain hypotheses unconfirmed. Preserve source roots and old artifacts; use declared storage floors and no commit/push/cleanup.

## Review Focus
- Native compounds, gemination, blanks and word separators must match CTC semantics.
- Silent/unknown evidence cannot become a confident deletion; ties remain uncertain.
- A high score for the supplied expected sequence is not itself proof of speech correctness.
- Synthetic planned text is not independently transcribed phonetic truth; all failures/denominators retained.
- Voice/action contracts must not carry recordings or strengthen unconfirmed hypotheses.

### Task1: Scorer and dataset
- [x] RED unit tests for exact CTC/brute-force probability, native compound equivalence, omissions/substitutions, ambiguity, empty/unknown/unsupported and no forced recognition.
- [x] Implement backend/app/vaakmitra_word/adult_sound_evidence.py with bounded canonical lattice/candidate scoring; GREEN tests.
- [x] Download/hash-bind pinned local TTS; generate fixed48base/192totalWAVs and reference/transform manifests with source/license and synthetic limits.

### Task2: GPU benchmark and decision
- [x] Freeze scorer/model/dataset/threshold identities; run actual frozen acoustic inference and compare old alignment/new CTC evidence on synthetic cases and existing public adult controls.
- [x] Publish counts by condition/kind, false-corrections, coverage/localization and raw token agreement. Keep all unscorable/long/failed rows.
- [x] Apply predeclared gate; no threshold search or retrospective relabeling. Clearly report qualified/inactive and natural-speech evidence limits.

### Task3: Mobile coaching and delivery
- [x] If qualified for benign coaching, port scorer with meaningful parity/erasure/uncertainty tests and feed existing local voice guidance, preserving raw predictions/avatars/session.
- [x] One fresh scoped review, single material-fix pass with regressions; full applicable unit/build/lint checks.
- [x] Preserve oldAPK/model and deliver newAPK onC if built. No phone actions while owner-deferred. Update report/context/ledger with exact evidence and pending real-mic/UI gates.

Task3 ruling: qualification failed; no native scorer port. Deliver a tested neutral-coaching fallback instead of promoting either unqualified sound-difference method. See ledger and ADULT_SOUND_TEST_REPORT.md.
