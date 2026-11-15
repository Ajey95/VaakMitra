# Autonomous Practice Cycles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Owner explicitly requests continuous implementation.

**Goal:** Repeated autonomous sound-learning cycles within each configured focus window, with bounded adaptive word sets/help and no child scoring.
**Architecture:** Pure ephemeral cycle/set policy plus foreground-owned cancellable cue scheduling in existing PracticeSession; reuse native phoneme evidence, authenticated refs, picture progress, existing mic and round praise.
**Tech Stack:** Existing Kotlin/Compose/coroutines/JUnit/Android instrumentation. No new dependencies.
**Spec:** ../specs/2026-11-13-autonomous-practice-cycles-design.md

## Global Constraints

SSOT3.3.61 DEC070/PHN011. Autonomous core stages/feedback/sets, Record/Stop remains explicit. No child wrong/mastery/diagnosis, raw evidence persistence/upload, unattended mic, weights/decoder/window changes,1665evaluation repeat, avatar/letter-unlock changes. Same isolated dirty lab worktree; no commit/push/cleanup. Preserve rollback APK/proofs.

## Review Focus

- ROUND auto-continuation must not reset the child's accumulated focus/session window.
- Same-set looping is finite and actually changes support/set for persistent unclear signals.
- Promotion uses independent task responses and bounded challenge, not fabricated phoneme correctness.
- Speech/timer/auto-next work cannot survive pause/Stop/background/account/target changes or overlap capture/praise.
- Public fixture auto-loop tests never start the microphone; legacy inert result fixtures stay inert.

### Task1: Pure cycle policy and focus clock
- [x] RED tests for repeated3-word sets, variable focus-derived budgets, stable vs unclear cycles, approved same/easier/harder selection, no wrapping outside plan, ROUND-only clock-preserving continuation and immutable actual-break gates.
- [x] Implement session-only cycle state and policy, authenticated-reference sound matching and independent picture-progress gates. Keep raw evidence out of reports/storage.
- [x] GREEN focused JVM suite.

### Task2: Autonomous guide integration
- [x] Replace child-selected Next-part/help-fade core with automatic bounded cue cadence and Your-turn/neutral feedback/next word. Reuse child Skip/Help/Stop controls and explicit mic.
- [x] Automatically continue completed ROUND only after cheer settles, preserving focus/session clocks; stop all delayed actions at lifecycle/identity boundaries.
- [x] New debug public autonomous fixture + meaningful rendered stage/automatic-choice/pause tests; retain old inert fixtures for unchanged reward/letter checks.

### Task3: Verify and deliver
- [x] One new scoped read-only review of autonomous extension (base review already done); fix material findings with regressions.
- [x] Full JVM/build/lint and installation/readback verification complete. Nine public UI checks passed on an earlier build; final 23-test physical qualification/screenshots explicitly deferred by owner (0 completed), not passed. Base rollback preserved; blocked instrumentation stopped.
- [x] Update delivery manifest/report/context/ledgers with evidence and remaining hardware/manual limits.

Final status 2026-11-13: implemented and installed; 235 JVM tests and build/lint passed. Owner chose "Finish the phone check later". Final physical qualification is the outstanding deferred gate; no background test or recording remains. See E:/VaakMitraModelLab/20261112-phoneme-transfer/AUTONOMOUS_PRACTICE_REPORT.md.
