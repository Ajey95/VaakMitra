# Learner-flow cleanup — DEC079 / UX014

User requested removal of app debugging instructions and verification of the intended end-to-end experience. This is Android UI/entry/packaging work. Model research remains on hold.

## Delivered behavior

- Introduction → Start learning → caregiver plan → familiar guide selection → Home. Local learning does not need a server/account. Caregiver sign-in remains a secondary choice.
- Every unconfigured profile, including authenticated profiles, reaches caregiver setup. Returning configured profiles reach Home.
- First-time guide save removes the introductory stack. Later Profile → plan → guide saves return to Profile; they do not reset the whole journey.
- Existing word/letter practice, autonomous support cues, manual microphone start, picture activities, voluntary breaks, summaries, sequential letter unlocking, avatar motion and three-turn reward rules remain in place.
- Letter completion confirmation sits below the teaching slate so wrapping feedback cannot push the next letter out of view at enlarged text sizes. The original 72dp readability requirement is retained.
- Learner copy no longer tells people to configure a PC/backend, use an offline engineering review, inspect development results or read diagnostic codes. Errors describe the available next action. Internal diagnostic evidence remains available to developers.
- Progress describes participation. Phoneme output remains an estimate; speech is not graded. No correctness/clinical flags were enabled.
- Therapist page truthfully states that no therapist/appointment is linked and opens practice progress. It does not pretend to book or send a reminder.
- A local profile marker is never attached to outgoing HTTP authentication. Caregiver-plan state is published only after its local write succeeds.

## Packaging

Reproducible entry: `scripts/android/build_offline_review.ps1`. Generated assets, app/project build outputs, temporary files and evidence are under `D:/VaakMitraBuildTemp/learner-flow-20261114`. Offline Gradle resolves the already installed tools/dependencies; the large global build-cache copy is disabled.

The debug review overlay includes the **unchanged retained baseline**:

| Item | Identity |
|---|---|
| Graph | phoneme.fp32.onnx, 1,262,607,977 bytes |
| Model SHA-256 | ff41636b23a41baa0ebb08e59f00fe684c9a054e40a9c41eb685542b5f5020cf |
| Vocabulary SHA-256 | 082feec079bf2cd65aa6b886d753a62c29d65ce0153cb0690968fe712d56e091 |
| Delivery change | Bundled asset, authenticated into the existing private cache on first use |
| Scoring/clinical/production flags | Remain false |

Build-time verification compares all source/staged metadata fields except the two delivery-only fields, and authenticates model/vocabulary bytes. The source bundle junction and source weights are not edited. No Gemma or rejected candidate is promoted. Release capture gates remain unchanged; these are debug review APKs.

## Evidence and checks

Evidence root: `D:/VaakMitraBuildTemp/learner-flow-20261114/evidence`.

- Entry/presentation tests were witnessed RED before implementation (`entry-red-corrected-launch.log`). An earlier argument-parsing failure is retained separately and is not counted as product RED.
- First full offline build succeeded: 275 JVM cases / 54 suites, zero failures/errors; lint passed with warnings; both APK variants and test APK assembled (`build-green.log`).
- One fresh source review found settings navigation clearing history. The actual emulator UI probe reproduced Home instead of Profile (`settings-return-red.json`, `settings-return-red-assert.log`); the initial-versus-settings flag fixes that path. No re-review was run.
- A subsequent build hit a full shared E-drive build cache while duplicating the model asset; no dataset/source cleanup was attempted. `--no-build-cache` avoids the redundant large cache copy. Failed log retained (`build-final.log`).
- Final product build passed (`build-final-no-global-cache.log`): 275 JVM cases / 54 suites, zero failures/errors, lint passed with warnings, both APK variants assembled. Generated debug overlay and both APK payloads independently authenticated; both APK signatures verify. Test-driver v4 and lint also passed (`test-driver-main-v4.log`).
- Actual fresh/returning learner journey **passed** (`learner-8g-v4.log`, 79.254 seconds). It exercised onboarding, local entry, caregiver nickname/plan, guide selection, Home/recreation, automatic word cue, enabled microphone readiness without recording, Amma picture matching, voluntary break/end, summary, progress, letter practice/unlocking to the second letter, Home next-letter persistence, Profile/settings save/return and relaunch. Nine real screenshots were captured; technical-copy sweeps passed at the visited states.
- The source-review settings regression has actual RED and GREEN evidence (`settings-return-red-assert.log`, `settings-return-green-dynamic.log`). The updated driver preserves the same avatars and verifies the actual Amma picture activity rather than assuming an action demonstration.
- Baseline native checks **passed** (`native-backbone-8g.log`, two tests / zero failures, 51.3 seconds): all 53 public clips match frozen desktop phone predictions and valid frame lengths; requested words do not force decoded phones; outcomes remain unscorable. This is execution/parity evidence, not pronunciation-error accuracy. Emulator median/max inference was 377/995 ms for these clips; it is not a physical-phone latency result.
- The full 78-case fixture run completed with 71 passes and seven failures (`ui-regressions-8g-v4.log`). Targeted reruns corrected stale-caption/scroll/timed-cue driver assumptions while preserving assertions about real controls, privacy, no report writes and reward timing. One genuine product issue remained: wrapped letter-completion feedback clipped the next glyph at enlarged text sizes. It was fixed by moving the confirmation below the teaching slate, retaining the original 72dp visible-size assertion. Failed runs remain preserved.
- Final layout rebuild **passed** (`build-layout-final.log`, 5m5s): 275 JVM cases / 54 suites, zero failures/errors/skips, lint with warnings, both review ABIs. Both new payloads and signatures were independently verified (`apk-verification-layout-final.log`, `arm64-signature-layout-final.log`, `x86-signature-layout-final.log`). These APK identities supersede earlier build identities.
- Final runtime rerun **passed all 14 cases** (`layout-regressions-final.log`, 243.109 seconds): all 13 alphabet/session cases plus the actual fresh/returning learner journey, on a fresh larger isolated emulator. This includes the large-text glyph fix, all letter categories, visible Stop controls, breaks, unlocking/persistence, word/picture/microphone readiness and caregiver settings return. Nine final journey screenshots and letter layout screenshots are saved in `learner-layout-final-screens` and `letter-layout-final-screens`.
- Across the full fixture run and the targeted reruns, **79 unique UI cases have a passing latest result, zero unresolved failures** (`ui-verification-summary.json`). This is combined evidence, not one clean 79-case run. Guide/reward/page fixtures were run before the final one-line layout relocation; all affected letter cases and the actual main journey were rerun afterward. No avatar or acoustic logic changed. Public-fixture microphones stay disabled; attempted taps cannot record or write reports.
- Final source snapshot: `source-manifest-final.json`, 521 inputs, SHA-256 `0b0ab058c5264bc54eb00067b6b41d6cb60b8e519aa74fe547a04dd55c15b819`, inherited dirty branch `codex/backend-verification-lab`, HEAD `712de54ee568da6262131f06092c0d4d251b2c92`. The earlier snapshots are retained.
- Native checks were repeated on the final APK and **passed both tests** (`native-backbone-layout-final.log`, 62.756 seconds): all 53 public clips retain desktop token/frame parity; requested targets cannot force the decoded phones; unscorable outcomes remain intact. Together with the UI evidence, 81 unique Android test cases have passing results. This remains model-execution evidence, not new adult/child sound-error accuracy.

The emulator uses a separate D-drive AVD/userdata, not an existing user profile or phone. Wi-Fi and mobile data are disabled. Cold boot resource kills and test-driver mistakes are retained as failed runs, not successful checks. The settled configuration uses API37 phone image / x86_64 / 16KiB pages, 8GiB RAM, four cores, host NVIDIA rendering and 720×1600 at density320. Model loading was killed for low memory in the 4GiB emulator (`native-model-exit-info.log`, explicit LOW_MEMORY); loading and parity succeed at 8GiB. This does not establish a minimum RAM specification for physical phones. Unrelated Google background apps were disabled only in this isolated test AVD; the system TTS package was retained. The installed API35 automotive image was not used; no new SDK was downloaded.

Replacing the last APK in the original 6GiB test userdata failed with `INSTALL_FAILED_INSUFFICIENT_STORAGE`. A new `VaakMitraLayout12` AVD was created from configuration only, with 12GiB userdata and the same CPU/RAM/display/image. Its first boot completed in approximately 195 seconds; both APK installations and the 14-case final run succeeded. The previous AVD, app data and authenticated model cache were preserved. No device data or project artifacts were deleted.

## Final review APKs

| ABI | Size | APK SHA-256 |
|---|---:|---|
| arm64-v8a | 1,341,469,343 bytes | 88b956d384693a63041bb0c4d65ddfd0a3051085b175234e8e09a0dcbd01cbdc |
| x86_64 | 1,347,814,710 bytes | cc73a435a5eb6f44ee365b2a25628394781e2f862cc9bf8fd6c5f613aa196512 |

Files are under `D:/VaakMitraBuildTemp/learner-flow-20261114/android/app/outputs/apk/debug/`. The graph is bundled uncompressed, so a fresh review installation does not require a PC model-transfer step. This makes the APK large; it is a debug review package with the existing release/scoring qualification gates preserved.

## Limits

No physical-phone install or test was performed in this task; owner deferred that check. Emulator UI/native parity do not validate child pronunciation assessment or therapy outcomes. No real microphone recordings were captured or sent to an LLM. Public-wave tests check retained-model execution/parity, not new accuracy. Tamil voice availability depends on an installed offline device voice; unavailable voice keeps practice accessible with clear guidance.

The working tree contains substantial inherited work. No commit, push, deployment, model training, source/data deletion or new exercise game was performed.
