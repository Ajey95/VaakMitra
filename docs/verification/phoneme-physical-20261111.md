# Physical phone phoneme smoke test — 11 November 2026

The retained V7 model was installed and its three native tests passed on the iQOO Neo7 Pro (I2217), Android16/API36/ARM64. Both installed app and test APK hashes match the verified local files. No model weights, phone inventory, decoder, VAD/trim reference or scoring behavior changed.

| Check | Result |
|---|---|
| Native fixture/parity/VAD/stress tests | 3 passed |
| Fixed public adult fixture after actual VAD/trim | Exact nine-phone reference; PER0 on this one fixture |
| Warm model inference,30 repetitions | Median15.28ms; P9527.41ms |
| Full public-fixture VAD/trim/inference path | 290ms |
| Synthetic stress files | Five conditions executed without model-unavailable error; no new per-condition phone PER calculated |
| App UI | Home -> Tamil Words -> Amma; ready microphone control |
| Live microphone | User confirmed phoneme preview after recording Amma; app-specific microphone operation observed (3.793s). No live audio or inferred phoneme labels captured by the agent; token accuracy not assessed |

These timings describe the named prerecorded fixture on one phone, not overall app response including recording, sustained load or battery consumption. The13.89% PER remains the earlier exposed adult107-clip desktop test result; it was not newly measured across the phone corpus. Official decision remains UNSCORABLE, approved_for_child_scoring=false and production_ready=false. No child, clinical or fresh-generalization claim.

USB file reads repeatedly disconnected and produced incomplete APK backups. Those partial bytes are not a valid rollback APK. The isolated official ADB37.0.1 copy lives at D:/VaakMitraData/envs/adb-37.0.1/platform-tools/adb.exe; original SDK untouched. Direct streamed installs succeeded with --streaming --no-incremental -r, keeping the existing package data through Android's update mechanism. Wireless pairing was not completed and was abandoned when the user requested USB. No pairing secret was saved. Large device-to-host USB transfers remain unreliable; their underlying cause is unconfirmed.

App SHA256: ddb9befd9afc61f0ea2c49df3977e66706ac6d32484b10b825c1eb70868d7742
Model SHA256: 94c30918c5be357d7384ddc6dd39fb65ed16ae80a507699b649332c049885683
Test APK SHA256: d80a4ba63b4e2b8177ab1ae3faa1aa2b774d30364c3a617dfcdc38a0ca8472cb

Authority: SSOT PHN001..006, DEC040/049. Native logs and phone-verification.json contain the measured evidence. Current V7 APK remains in the existing round5 delivery. Rejected V8 remains excluded.

Live-smoke completion: the user explicitly reported “Phoneme preview appeared.” This is user-confirmed end-to-end functionality, corroborated by the app-specific recent RECORD_AUDIO operation. It does not establish the correctness of the predicted phonemes, a new PER or child performance. The app remains installed for continued manual word practice.

**Subsequent live recognition failure:** the user reported inconsistent phoneme outputs while repeating Amma. The native tests and displayed preview demonstrate execution only. Live phoneme recognition is unreliable; the model is not established as suitable for pronunciation feedback. See ongoing phoneme-live-debug-20261111 diagnosis.
