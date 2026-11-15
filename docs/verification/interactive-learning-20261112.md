# DEC-059 internal interest learning — 12 November 2026

**Later physical-phone follow-up:** the same installed ARM64 APK passed40/40native checks on the user's iQOO/API36. Normal and2x interest screenshots were inspected and MainActivity reopened after intermittent USB recovery. Initial phone-unavailable statements below describe the earlier emulator delivery snapshot. See [phone verification and transfer limits](interactive-learning-phone-20261112.md).

SSOT3.3.44, DEC059/060, ILR001..011. This update adds a fully on-device picture-task learning loop to existing word practice. It does not improve or validate phoneme recognition, diagnose difficult sounds, or demonstrate speech-therapy effectiveness.

The learner chooses train, animal or story scenes inside the existing session. Known-word picture choices change the level of picture support. Two matching turns try less help; errors or Show help restore it. More repeats without requiring a picture or speech score; Enough ends the session and cancels audio. Three turns, focus limits and session limits introduce breaks with explicit resume. App background/restore pauses the activity; no picture action starts recording or speech playback.

Help changes the active session immediately, even when saving fails. Confirmed durable history remains unchanged until a successful commit; later hint-free counts follow the support actually displayed. While verified history loads, picture actions are disabled with a loading message, rather than acknowledging taps that could disappear. Every deferred update carries its initiating owner. Picture captions remain visible at all support levels, and the option policy excludes the known Help/What and Want/Hand symbol pairs.

Next activity stays within the selected 18-word or 25-word itinerary, using picture-task history to adjust upcoming challenge or revisit earlier-day practice among remaining words. It does not classify a child's speech difficulty. With no history the original itinerary is retained, and the last item ends rather than wrapping.

Writing parts show Unicode-safe Tamil written units only. Existing whole-word Example playback remains the audio option. These are not approved syllable recordings, shorter spoken words or sound-error remediation. The 247-letter sessions, manual letter unlocks, avatars, catalogue IDs and model assets are preserved.

No caregiver rating, external service, chatbot, generated media or cloud speech API is required by this loop. Verified account/child identity scopes private local progress. Unknown identity and public debug previews remain session-only. Failed commits are not acknowledged as saved, and changing identity hides stale history. Reports count picture turns, matches, turns without extra hints and help requests separately from experimental voice attempts. A picture match is never speech accuracy or mastery. Older reports lacking a verified owner are hidden without deleting their stored data. Automatic therapist report delivery is outside this change.

## Verification

Analysis: `D:/VaakMitraData/analysis/interactive-learning-20261112`. Spec and plan: `docs/superpowers/{specs,plans}/2026-11-12-interactive-learning*.md`. Ledger: `.superpowers/sdd/2026-11-12-interactive-learning/progress.md`.

- Pre-review local build: 130 JVM tests, zero failures/errors/skips; Android lint zero errors and seven existing warnings; ARM64/x86_64 main and instrumented test APKs built offline. After the review fixes, 136 JVM tests passed; final package/native verification follows below.
- Meaningful RED to GREEN coverage includes scoped confirmed writes, report ownership, support restoration at saturated counters and prior-day revisit scheduling. Compiler errors are recorded separately from behavioral regression failures.
- Pre-review native full suite passed 39/39 on its SHA-bound build. Six new public-preview smoke cases also passed on their separately recorded build. After fixes, final 40-case emulator verification must be separately bound; earlier successes are not proof for a later APK.
- Protected hashes: 15 files unchanged (12 model/reference assets and three avatar source files). Each main APK contains all 12 identical assets; APK CRCs checked. `artifact-verification.json` records final hashes/results.
- Screenshots use app-window PixelCopy from inert public previews, including 2x text. Tests do not record private microphone/camera input or write private account history.
- Phone disconnected before the install was confirmed. No phone installation, phone UI verification or phone model test is claimed for this build yet.

## Retained speech model and limits

V7 ONNX SHA256 `94c30918c5be357d7384ddc6dd39fb65ed16ae80a507699b649332c049885683` remains unchanged. Official result remains UNSCORABLE; `production_ready=false` and `approved_for_child_scoring=false`. Historical 13.89% exposed adult old-19-word PER is not a current child or new-word accuracy claim. No training, new recordings or dataset transfers occurred in this update. Child learning benefit, attention duration and speech gains require separate observation and evaluation; the new UI does not establish them.

Cloud spend for this update: ₹0. Local electricity was not metered. Existing optional account/backend screens are outside the offline learning loop.

## Fresh review and fix pass

One fresh read-only gpt-6-astra/high review found five Important issues, no Critical issues and one Minor. All five Important findings were retained by learner-visible effect and addressed in one author fix pass, without a second review:

1. Current word, turn feedback, pacing, session ID/start, bounded activity counters and known microphone-word IDs restore in one identity-keyed Compose namespace. Native recreation after advancing/matching Appa was witnessed failing against the old installed main APK, then covered in the final suite.
2. A verified store's loading state differs from ephemeral practice. Profile binding/updates serialize, and both load completion and delayed taps carry their initiating owner. A loading tap cannot be acknowledged; stale-owner updates are rejected.
3. Active-session support is immediate and separate from confirmed storage. A failed write cannot withhold requested help or make the next selection incorrectly hint-free.
4. Captions stay visible and known confusable symbol pairs are excluded across all25 targets, two/three options and101turn seeds. The policy regression first failed with135tests/1failure before the fix.
5. Ending carries the current owner-bound session report and honest save status to the summary, including ephemeral or failed-save sessions. A failed write preserves the previous confirmed durable report; late-origin saves cannot publish under a new owner. Confirmed report and owner are one atomic memory record.

Regression contract interfaces were initially RED (missing new state helpers); this is distinct from the witnessed behavioral policy/native failures. Deterministic injected storage failures and owner transitions exercise state contracts; real private storage-failure I/O was not performed. Review evidence and all author rulings are in the ledger and `final-review.md`.

Deferred Minor: the summary's existing Words metric counts only distinct microphone-attempt words. Picture counts are shown separately, but the Words label could be clearer. This update does not claim picture-only turns are spoken words.

## Final completed verification

Final build succeeded in4m4s: **136/136 JVM tests**, zero failures/errors/skips; lint **0errors/7warnings**. Main ARM64/x86_64 and instrumented APKs built. Final installed emulator main and test SHA256 values were read back and matched before **40/40 native tests** (19 retained letter/model/reference checks plus21gallery/flow cases). The recreation regression now retains Appa, its matched state and both picture matches in the session-only summary after explicit resume. The app was reopened in MainActivity after the suite. All35public screenshots were retrieved; normal and2x interest screens inspected. All15protected file hashes and12assets inside each APK matched the before manifest; ZIP CRCs passed.

| Artifact | SHA256 |
|---|---|
| ARM64 debug APK | `c42d150a1f1cc2d8e73706ee359d5240bb041099afb039d5adb2fcb1db1364d7` |
| x86_64 debug APK | `67b9662ad7a80f9763220856b9e57d3c4da3bdb47b45082ee70eee9177a883e9` |
| Instrumented test APK | `a9d29f86610750b1ca53387b7ffb9dc59eaac2ef2497ee41aa173a71cc282a16` |

Phone still absent from ADB at final check: installation, physical-phone UI, microphone and Tamil voice behavior remain unconfirmed for this build. Tests use public inert fixtures and injected failures, not consented child trials or private device storage failures. The fresh AI review preceded the one fix pass; author test evidence closes the findings, without claiming a second reviewer approved the final diff.

## Delivery

Package: `D:/VaakMitraData/deliveries/interactive-learning-20261112`, with scoped source, verification evidence and public screenshots. `APK-location.json` identifies the verified ARM64 APK and whether it could be copied within the250MiB disk reserve. If not copied, use its recorded build path; do not assume an APK exists in the package. Emulator APK remains at `SpeakEasyAndroid/app/build/outputs/apk/debug/app-x86_64-debug.apk`. Prior focused-word delivery is retained for rollback. No commit, merge, push or cleanup is authorized or performed.
