# VaakMitra Android Review APK Implementation Plan

**Goal:** Deliver the SSOT-compliant, installable Android review APK described in `docs/superpowers/specs/2026-09-15-android-review-apk-design.md`.

**Requirements:** DEC-012/013/014/019/020/021/025/026/027.

- [x] Add test-first pure Kotlin domain for caregiver plans, the canonical 19-word starter catalogue, checkup states, and event-derived session summaries.
- [x] Add DataStore persistence for review-demo identity, child plan, checkup metadata, and compact session summaries without raw audio/transcript/embeddings.
- [x] Add debug-only offline review entry and caregiver setup screen.
- [x] Rework Home and Words into the approved daily-plan and readable word-path layouts.
- [x] Connect Practice break/stop/attempt events to a truthful Session Summary.
- [x] Replace fictional Progress metrics with locally recorded event metrics and add the fortnightly checkup screen.
- [x] Update navigation, profile entry points, and accessibility labels.
- [x] Apply the DEC-027 snuff/maroon visual system using the owned calm-market project as interaction-language reference.
- [x] Run JVM tests, lint, debug build, inspect APK, hash it, and update verification documentation.
