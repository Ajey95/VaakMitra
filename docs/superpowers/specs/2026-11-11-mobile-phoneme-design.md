# Mobile phoneme transfer experiment

User authorized local RTX 4060 training, synthetic robustness testing, and Android integration after discussing this design. Use the existing lab worktree, preserving all prior dirty work. No cloud resources or costs.

Reuse every encoder tensor from mobile-student-ta19-v1/training/mobile_word_student.pt. Reduce the final two encoder strides to 1 (40 ms output instead of 160 ms), then add a two-layer bidirectional GRU and a phoneme CTC head. These new layers are initialized afresh; the acoustic encoder is transferred and fine-tuned. Predicted tokens must come from audio, never target-word lookup.

Use the existing 15,972 machine-filtered, segmented adult word recordings and the frozen private lexicon. Preserve speaker splits, reject audio duplicates across splits, and select checkpoints only on calibration PER. Upweight 19 app words. No child data has been provided for this run. Inventory is provisional and outputs are engineering token predictions, never child correctness scores.

Use an isolated CUDA PyTorch environment on D:. Training normalizes DC and RMS inside the graph, accepts 3 s padded waveform input, and excludes examples needing cropping. Synthetic training noise/volume changes are bounded; robustness testing generates separate noise/echo/filter/gain variants only from held-out evaluation recordings. No vowel-duration/pitch transforms. Store generated WAVs and metrics outside Git with source-parent binding.

Export FP32 and dynamic INT8 ONNX; choose INT8 only after token agreement and PER comparison, retain FP32 fallback. Android uses local ONNX CPU inference, exact input/output names and shapes, SHA-256 verified weights/vocabulary, blank-collapse CTC decoding. Run on VAD-selected audio without target-duration normalization. Show transient predicted tokens in the debug practice UI; no phoneme/audio persistence or logs. Existing official UNSCORABLE status persists.

Completion: CUDA run evidence, selected checkpoint/manifest/hash, clean + synthetic held-out metrics, desktop/ONNX parity, JVM decoder tests, Android unit/lint/build, APK and physical execution if a device is available. Report any missing gate explicitly. Do not equate packaging with acceptable accuracy.

Implementation ruling after calibration runs: the full transferred word encoder plateaued at target PER ~.24-.30. Compare a five-module early encoder (same transferred weights, ~265ms receptive field) with the seven-module version (~905ms), both emitting 75 frames for 3 s input and both using the same weighted calibration selection score (.7 target19 PER + .3 overall PER). All new recurrent/head weights are initialized, then trained; audio encoder tensors are copied from the saved word model. Keep the full-encoder checkpoint as baseline. Select using calibration only; no child recordings supplied. User chose emulator-only deployment testing for now.
