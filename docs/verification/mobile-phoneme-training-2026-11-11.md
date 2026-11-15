# Local phoneme transfer run - completed evidence ledger

## Authorized objective

Fine-tune the existing mobile encoder on the RTX 4060 Laptop GPU, generate synthetic held-out robustness WAVs, integrate true audio-derived token predictions into Android, and deploy/test on an emulator (user selected emulator for now). All work is a provisional adult-data engineering experiment. Child vowel recordings mentioned by the user have not been supplied and are not part of this run.

## Inputs and isolation

- Lab worktree: D:/VaakMitra-Integrated-Backend-Lab, branch codex/backend-verification-lab, original HEAD 712de54ee568da6262131f06092c0d4d251b2c92. Existing unrelated dirty work preserved.
- Base trainable checkpoint: D:/VaakMitraData/artifacts/mobile-student-ta19-v1/training/mobile_word_student.pt, SHA256 e136e6f6438f681b3832e41e8fbb064fe6403448553b80f75213ed57fd4d1649.
- Audio: D:/VaakMitraData/prepared/openslr127-word-v1; source openslr127-word-v1-reviewed.jsonl. 15,972 machine-filtered clips, 12,677 train / 1,630 calibration / 1,665 held-out evaluation. Target19 counts 985/105/107. All 15,972 exact words matched the frozen private lexicon; every WAV hash checked before cache creation.
- Full split, WAV hash, source/base/vocabulary/cache digest checks; prepared row metadata frozen in input-binding.json. Future checkpoints include prepared dataset SHA and encoder depth.
- Isolated environment D:/VaakMitraData/envs/phoneme-cu124, Python3.12 / Torch2.6.0+cu124 / NumPy1.26.4 / ONNX1.17 / ORT1.21.1. Default system Python CPU install preserved.

## Measured setup gates

- GPU visible: NVIDIA GeForce RTX4060 Laptop GPU, 8,188 MiB VRAM.
- CUDA forward/backward canary: 10 updates in 3.359 s, peak allocation 231,835,136 bytes, finite losses 48.41 -> 13.10. See D:/VaakMitraData/artifacts/phoneme-ta19-v1/gpu-canary.json.
- Sixteen focused Python tests passed: transfer/temporal shape, early transfer, CTC blank/repeats, normalization, speaker/audio split rejection, deterministic stress, INT8 target gates, metadata/cache/vocabulary tampering, prior mobile model tests.
- JVM decoder tests passed; full Android unit tests, lintDebug, AndroidTest Kotlin compilation passed before final test-fixture edits. Final built-model native tests still pending.

## Training decisions

- Baseline seven-module encoder: new BiGRU/CTC head, reduced last strides, 61 output units including blank. 30 initial epochs then refinement through epoch38; best weighted calibration score ~.3569, target PER .2431 at epoch26. Preserved phase1-best/last and full-encoder-best.pt. No baseline held-out evaluation generated before comparison.
- Ruling: suspected word-encoder smoothing; compare early five-module pretrained features while retaining 40ms frame outputs. Same speaker splits and selection metric. New candidate root D:/VaakMitraData/artifacts/phoneme-ta19-v2-early. Cache is a read-only-use hard link to baseline cache, metadata copies have same hashes. Do not modify either cache.
- Training and format selection use calibration; synthetic robustness derives from evaluation examples only. No synthetic child voices or pronunciation-error labels are fabricated.

## Completed delivery gates

- Selected early encoder, epoch22: calibration target PER17.18%, held-out target PER28.33%, exact54/107. The broader-vocabulary PER61.15% and target results limit this to an experimental preview.
- FP32 ONNX is1,171,172 bytes; 290,701 parameters. INT8 failed the overall98% calibration sequence-agreement gate. CPU PyTorch/FP32 ONNX decoded sequences agreed on all1665 held-out clips. All15 transferred encoder parameter tensors were updated by training.
- Generated535 held-out stress WAVs with source hashes and attribution. PER: noise20 28.70%, noise10 31.85%, echo26.85%, lowpass28.33%, quiet28.70%. Source evaluation clips never entered training.
- Hash-verified bundle copied into main app assets; public test WAVs only in AndroidTest assets. Updated UI wording to describe phoneme predictions accurately.
- Final build:56 JVM tests, lintDebug, ARM64/x86_64 APKs and AndroidTest APK passed. Three native tests passed on Android14 emulator after final APK installation. Thirty warm inference repetitions: median146.27ms, P95155.68ms in the final run. Actual VAD/trim/model fixture:727ms including setup,9/9 phones matched. Five synthetic native variants returned tokens without model errors and retained UNSCORABLE.
- Emulator practice UI inspected. Installed x86_64 base.apk SHA256 ebf091810f4a11916c07d2f424c753fb59532091c9bfa37390e8689e2e356136 matches the delivered x86 APK. ARM64 model asset hash also verified; physical phone testing was not requested for this stage.
- Delivery files are in E:/Codex/2026-11-09/au/outputs: APKs for both ABIs, model/evidence ZIP, results Markdown and delivery JSON. Synthetic audio ZIP remains in the selected D: run root.

## Operational notes

E: has little free space; environments, cached audio, generated WAVs and new emulator images are on D:. Existing Pixel_7 Android37 preview boot failed. A stable Android14 image was downloaded from Google's repository, checked against official SHA1 e0f6c9a0691aa27bd597d0deb1bcfdc943ac8ca7, and installed under D:/VaakMitraData/android-sdk. The task AVD is Phoneme_34 under D:/VaakMitraData/emulator-avds. No user files deleted or original emulator data moved. No cloud GPU resources were created.
