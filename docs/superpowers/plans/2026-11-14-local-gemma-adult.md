# Local Gemma Adult Benchmark Implementation Plan

> REQUIRED SUB-SKILL: superpowers:executing-plans, inline. Use a single final source reviewer only after an actually runnable inference integration; no implementer agents or repeat reviews.

**Goal:** Measure whether offline Gemma4E2B corroboration improves adult omission/substitution detection over the retained phoneme model.
**Architecture:** Target-blind local audio observations, strict parser/loopback client, frozen acoustic evidence and matched threshold comparison; inactive research code.
**Tech Stack:** Python stdlib/numpy/existing pytest, pinned CUDA llama runtime and Q4/Q8 Gemma GGUF.
**Spec:** ../specs/2026-11-14-local-gemma-adult.md

## Global constraints

DEC078/PHN019, SSOT3.3.76. Adult public data only; no LLM/cloud audio transfer, child/private audio, Android/UI changes, audit consumption, source deletion or paid resources. Literal127.0.0.1 endpoint, no redirects/proxies; audio memory only. Research D<=10MiB/D>=250MiB. New model drive requires8GiB initial free and2GiB projected reserve; C>=512MiB, E readonly until qualified.

## Review focus

- A successful text response must not be mistaken for audio support or phonetic evidence.
- Target knowledge/normalized transcripts must not leak into independent observed phones.
- Loopback redirects/proxies/cloud fallback must not transmit recordings externally.
- Unsupported/ambiguous/invalid outputs stay in denominators and never become a correction.
- Laptop GPU success must not imply native mobile, child or clinical readiness.

### Task1: Metadata/storage preflight and research contracts

- [x] Freeze exact model/runtime metadata and existing evidence/source hashes before inference; inventory installed candidates and disk capacity.
- [x] RED tests in backend/tests/vaakmitra_word/test_local_audio_research.py for strict observation schema, no-target prompt, loopback-only client, ambiguous/unknown abstention and exact corroboration with body-bound existing gate.
- [x] Implement backend/app/vaakmitra_word/local_audio_research.py; GREEN. No product imports.

### Task2: Matched benchmark runner

- [x] Create scripts/model/benchmark_local_audio.py with prepare/smoke/development phases, source audio hash checks, memory-only loopback WAV requests, model/runtime/source identity freeze and no test-panel reads.
- [x] Test protocol/panel completeness, malformed local responses, zero/invalid control and source bounds; meaningful backend regression suite sequentially.
- [x] Download/run pinned local CUDA runtime/model only after space qualifies. GPU execution verified; structural smoke FAILED. SSOT3.3.77 allowed same159source descriptive completion with failed gate preserved and no winner, tuning or audit activation.

### Task3: Disposition

- [x] One fresh source review plus one material RED/GREEN fix pass; pre-inference path plumbing regression and diagnostic no-selection guard tested; no re-review or fresh audit.
- [x] Record measured negative results; update project context/ledger, preserve avatars/session and deployment state.94tests passed;541Android proof files unchanged. This experiment is complete; reliable sound detection and offline mobile deployment remain unresolved.
