# Personalised encouragement implementation plan

> Execute inline with superpowers:executing-plans; meaningful RED/GREEN, ONE fresh final reviewer and ONE Important correction pass, no rereview. Existing dirty isolated lab stays in place; no commits/merge/push/cleanup.

**Goal:** personal Tamil effort feedback with controllable offline speech and a brief celebration.
**Architecture:** pure closed praise/settings/delivery policy; scoped settings store; reusable Compose panel; same active practice speaker and separate lifecycle-owned summary/preview speaker.
**Tech stack:** existing Kotlin/Compose/Android TTS, no dependencies.
**Spec:** docs/superpowers/specs/2026-11-12-personalised-encouragement-design.md

## Global constraints
- SSOT3.3.48 DEC062/063/064 PRS001..007; preserve all25words/247letters, avatar sources, model/reference assets and UNSCORABLE gates.
- Automatic appreciation ON for unsaved settings, explicit opt-out preserved, no external synthesis/film media, public previews never speak or write private settings; public explicit audio probe separate.
- Existing Stop/microphone/owner/navigation priority; no invented stars/correctness/attention or child-benefit claims.
- D250MiB packaging reserve, scoped before snapshots and compressed current ARM rollback; no unrelated cleanup.

## Review Focus
- A name, setting or queued speech from one owner cannot reach a new profile after a delayed callback.
- Replay, background, re-entry, rapid taps and enabling audio cannot restart or queue old cheers over a microphone/Example.
- Empty/failed/unsupported sessions and unapproved acoustic results cannot earn a stamp or alter stars/unlocks.
- Tamil/mixed/empty/hostile names, missing voices, slow callbacks and save failures stay intelligible and usable.
- Normal/2x layouts and motion-disabled/Still settings preserve meaningful feedback and reachable Stop/Continue/End.

## Task1 policy and audio
- [x] Write pure praise/name/participation/settings/delivery/failed-owner-write contracts and observe RED; implement journey/Encouragement.kt and scoped EncouragementStore.kt with GREEN.
- [x] Extend LocalTamilSpeaker with a closed personalised-praise entrypoint and reset per-utterance voice parameters; retain offline selection and cancellation. Add public-name native speech probe with explicit availability evidence.

## Task2 native feedback and handoff
- [x] Add ui/components/EncouragementPanel.kt with bounded print-medallion animation, name/caption, replay/stop and preview/settings dialog; use same speaker in PracticeScreen and lifecycle-owned speaker elsewhere.
- [x] Wire explicit word activity/result encouragement, manual letter completion/round/summary and nonempty word summary; Rewards settings preview. Add only optional parameters to existing session/navigation wiring; preserve legacy stars and letters.
- [x] Native missing-feature RED, then normal/2x/settings/participation/restore/Stop checks GREEN; run full appropriate JVM/lint/APKs and retained/gallery checks sequential to heavy builds.
- [x] ONE fresh read-only review; grade by learner effect, one Important TDD pass, no rereview; ledger all rulings/deferred minors. Verify assets, installed APKs, actual voice availability and rollback; update context/report and separate source/evidence delivery.

DEC063 addendum: each actual completion arms one ephemeral owner-bound ticket. Typed mailbox claim/current/cancel prevents duplicate, stale-owner and old-screen cancellation of a newer summary. Automatic speech has a four-second foreground voice-initialisation budget and synchronous Stop/background cancellation; restored progress cannot arm a ticket. Add no-replay-tap native cases for words, manual letters, rounds and a new participating summary.

Verification scope: current physical iQOO runs all19retained+43gallery checks (62), and x86 emulator runs5model/ABI+all13new automatic-feedback UI checks (18). This covers full production UI on its actual mobile target and targeted older-OS/x86 parity, without repeating unchanged emulator legacy gallery cases. Record this limit explicitly rather than claiming62onboth.

Completion evidence:171JVM; lint0errors8warnings; phone62, emulator18 native checks; fresh physical offline probe1/1. USB drops limit phone image export to1complete/2failed/42unattempted, final post-probe foreground unconfirmed. Four emulator normal/2x images and one phone Rewards image inspected. Source/evidence handoff preserves this limit; no child/clinical or audible no-tap E2E claim.
