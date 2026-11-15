# Adult Development Chunk-and-Blend Coach

Authority: `VAAKMITRA_FINAL_SSOT.md` v3.3.2, DEC-023 and DCH-001..005. This is an isolated adult engineering demonstration, not child pronunciation treatment or a release claim.

## Flow

The operator opens the existing loopback adult lab, selects a Tamil target, and submits a consented adult whole-word recording. The real diagnostic returns its existing `UNSCORABLE` result and an additional ephemeral `chunk_coach` object. The coach divides the canonical target into one to three nonempty *written* chunks and, only when a valid capture produced a distinct Tamil top candidate, highlights the chunk containing the first text difference. The focus is explicitly an ASR text hypothesis, never an observed sound error. The operator can override the focus.

The UI then walks through `focus` → `blend` → `whole_again`. Focus and blend are visual/unscored. An optional locally installed Tamil browser voice may pronounce the chosen chunk or whole word for this adult-only demo; no voice means text-only mode. The operator says the chunk aloud without capture, advances to the blend, then records the whole target again through the existing bounded adult WAV endpoint. Two completed coaching cycles cap the demo; the UI offers a break/reset. Clear, close, target change, unmount, or microphone start cancels any prompt playback. While a prompt plays, the microphone cannot open.

## Boundaries and payload

`chunk_coach` is returned only by `/api/dev/word-lab/assess` behind the existing loopback/operator capability. It contains `status`, `target_word`, `chunks`, `focus_index`, `focus_position`, and `basis`; it does not expose an audio segment, timestamp, phoneme label, score, diagnosis, or child identifier. `status` is `text_hypothesis` only for a valid distinct Tamil candidate; otherwise `visual_only`. `basis` is always `unvalidated_asr_text_difference` or `manual_visual_practice`. The response is never persisted. Existing official decision remains `UNSCORABLE` with null decision probability. Child/session APIs and Android scoring remain unchanged.

## Chunk derivation

Use Unicode NFC, reject empty/non-Tamil input, and group Tamil base letters with following combining marks/virama to keep written clusters intact. Prefer two chunks for short multi-cluster words and three for longer words, preserving exact reconstruction and no empty chunk. Locate the first mismatched written cluster by comparing target and candidate sequences; map that index to its containing target chunk. Identical/missing/invalid candidate or invalid capture has no automatic focus. This is visual orthography, not a validated Tamil syllabifier.

## Failure handling and tests

Backend tests cover exact reconstruction for `அம்மா` and longer words, malformed/identical/cross-script candidate fallback, quality gating, and endpoint isolation/null decision. Browser tests cover displayed hypothesis disclaimer, manual focus, focus/blend/whole-again loop, two-cycle cap, no chunk upload, target/clear/close reset, and local-voice absence. A real adult-audio loopback smoke checks the actual endpoint response. No child recordings are used.
