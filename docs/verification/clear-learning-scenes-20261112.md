# Clear learning scenes — 12 November 2026

The Android word activity now uses explicit illustrations and clearly labelled Train, Animals and Storybook scene choices. Changing a scene keeps the practice word, avatar, voice controls and current activity evidence. The chooser starts closed, shows bilingual names and previews, and brings the selected scene back into view. Static progress advances only with voluntary activity turns and stops at three turns before a break.

## Teaching content and limits

Six concrete words use curated matching: Amma, Appa, Unavu, Thalai, Kai and Veedu. Amma and Appa show a mother/father with a child and explicitly say Family example. These are illustrative relationships, not identification of the learner's actual family. Each picture is a single accessible, tappable card including its captions and padding; two/three-choice pools use meaningful alternatives. Figures preserve their proportions in wide frames. The hand has four fingers and one thumb.

The other 19 words use individual before/after contextual examples rather than arbitrary correct pictures. For example, Vendum shows requesting a ball; Aam shows accepting it; Enakku indicates the recipient. Distinct meanings have distinct visible actions. Show the action and See it again are the real controls, with optional whole-word Example audio and microphone. Exploring a demonstration records a separate activity count, never a correct picture answer or speech score. Writing parts remain written units, not generated spoken syllables.

Train, elephant/Animals and Storybook illustrations provide a chosen play setting. They do not change the word or diagnose attention, comprehension or pronunciation. No timers, automatic sound or looping stimulation were added. More, Enough and Break / Stop remain explicit. Word-session background restoration preserves a partial three-turn round and its focus budget; explicit Continue remains necessary. Existing letter-session behavior is retained.

## State and compatibility

Word-learning v2 uses a separate private namespace and schema, retaining legacy stored files. Old glyph responses cannot seed new illustration difficulty. Contextual targets cannot earn picture matches through UI, direct selection, report or history paths. Extra help is tracked synchronously per turn, including when storage is loading or a prior write is pending, so a supported response cannot become a hint-free match. Existing owner isolation, last-confirmed writes, legacy report defaults and bounded counters remain.

All 25 word routes, the 18-word focused itinerary, all 247 letters, manual letter unlocking, avatar sources and 12 packaged model/reference assets remain. V7 ONNX SHA256 is `94c30918c5be357d7384ddc6dd39fb65ed16ae80a507699b649332c049885683`. Official status remains UNSCORABLE, production_ready=false and approved_for_child_scoring=false. No model training, new recordings, dataset changes, cloud service or API key was used. No speech-accuracy, child-learning or clinical-benefit improvement is claimed.

## Verification

Final JVM result: 150 tests, zero failures/errors/skips. Lint: zero errors, eight warnings (seven inherited and one new optional-parameter-order warning). Both ABI APKs and instrumentation APK built. All 15 protected file hashes are unchanged, all 12 protected assets match inside each main APK, and APK ZIP CRC checks pass.

Native final results and screenshot inspection are recorded in the completion addendum below. Public adult fixtures and inert previews exercise the production UI without real microphone recording or private-account writes. Test APK and installed main APK hashes are read back before native execution. Earlier failed runs and earlier images remain explicitly historical, not final evidence.

## Review and resource decisions

One fresh read-only final AI review found no Critical issues. Five Important findings plus hidden selected-scene feedback and indistinguishable contextual actions, regraded Important, received one RED-to-GREEN correction pass. No rereview was requested. Native regressions cover actual focused accessibility names, rendered hand anatomy, distinct action pixels, correct contextual guide copy, partial-round restoration, selected-scene visibility and two/three-choice touch bounds at double text size. Unit contracts cover pending/loading support accounting and word-only pacing restoration.

Two Minor issues remain: contextual help uses the historical PictureHelp/report section label, so zero picture turns can appear beside help requests; and the new illustration composable has an optional-parameter-order lint warning. Counts remain separate from speech. Actual TalkBack spoken output, live private persistence and child comprehension/attention were not validated.

Low host space caused transient dips below the intended 250 MiB reserve during installation/build work. Generated build artifacts and the dedicated task Gradle cache were transparently NTFS-compressed without deletion; APK hashes remained identical. This trades read-time decompression CPU for disk space and does not establish a long-term storage solution. Prior ARM APK SHA256 `c42d150a1f1cc2d8e73706ee359d5240bb041099afb039d5adb2fcb1db1364d7` is retained and ZIP-verified at `D:/VaakMitraData/analysis/clear-learning-scenes-20261112/rollback-arm64.zip`. Earlier delivery manifests remain frozen; their mutable build-path locators are historical, not current APK bindings.

Repository remains on the existing dirty `codex/backend-verification-lab`, HEAD `712de54ee568da6262131f06092c0d4d251b2c92`. No commit, merge, push, reset or cleanup. Protected original roots were read-only. Local electricity is unmetered; new cloud/API spend was zero. SSOT 3.3.45 / DEC061 / ILR012..016, spec, plan and the execution ledger define the scope.

## Completion addendum

- emulator: 49 passing native checks (19 retained on unchanged production main + 30 final gallery), 41 complete screenshots, 0 retrieval errors. MainActivity reopened: True. Installed main SHA256 `d38d8cac2b631dff0860b9f3fd602e7a07a8d603a1571e1e5e93db11aab4b84c`; test `d38cf233271e732425d56764bf223564e68326c1f284b65f1a6ddad529fbd13a`.
- phone: 49 passing native checks (19 retained on unchanged production main + 30 final gallery), 41 complete screenshots, 0 retrieval errors. MainActivity reopened: True. Installed main SHA256 `f1ba41c588f54fe94c3d4a1e0c6cc8a8556d063b81115af73656ecda99dc73f5`; test `d38cf233271e732425d56764bf223564e68326c1f284b65f1a6ddad529fbd13a`.

The nine new focused cases also passed separately on the final emulator APK. Five fresh normal/double-text screenshots were inspected using view_image; observations and hashes are in visual-inspection.json. Each device has 19 retained checks on the identical final production main with frozen test APK c257db915633beae008fff01b73f518a2c7f56a6ac9bad75330a7215c6657853, followed by 30 final gallery checks with the final test APK. The retained sources did not change; only physical-caption test diagnostics/stable viewport setup changed between test APKs. Both run bindings are retained rather than implying a single test APK was used throughout. Any screenshot download failure is an artifact-retrieval limit, not a passed or failed native assertion. No real child/adult microphone utterances were captured in these checks.

ARM APK location: D:/VaakMitra-Integrated-Backend-Lab/SpeakEasyAndroid/app/build/outputs/apk/debug/app-arm64-v8a-debug.apk. Delivery: D:/VaakMitraData/deliveries/clear-learning-scenes-20261112; APK-location.json binds its exact location/digest and states whether an extra copy fits the disk reserve. Twelve key final screenshots, complete run logs/bindings, JVM XML, lint XML and both test APKs are copied; the complete public screenshot galleries remain at the hash-bound analysis paths to preserve disk reserve. The source/evidence snapshot is separate from all earlier deliveries. Final manifest and disk measurement are retained with the delivery.


Accessibility implementation reference: [Android Developers: merging and clearing semantics](https://developer.android.com/develop/ui/compose/accessibility/merging-clearing). Native diagnostics first reproduced a labelled nonclickable child inside the full-card action; clear-and-set semantics now exposes the Tamil word, caption and action as one control. The strict clickable-node assertions were retained.

Earlier phone gallery evidence includes one caption-touch timeout: the unchanged action assertion passed in isolation, then the harness was strengthened to request the card on screen and require three stable geometry samples before the original physical tap. Its final complete 30-case gallery passed. The exact cause of the original missed tap remains unconfirmed. An earlier emulator gallery had one preview-launch callback timeout while compilation ran; its final complete 30-case gallery passed after compilation finished. Production main APK bytes did not change during these test-only diagnostics. Failure logs and their original bindings remain alongside the final results.

Final author inspection additionally covered three fresh phone images: complete family cards before physical touch, the scrollable scene chooser and all three choices at double text. The phone chooser frame shows Train/Animals with Storybook below the current scroll position; native assertions verify the third row is reachable. See visual-inspection.json for observations and exact image hashes.
