# Benchmark reports

Generated JSON reports belong here only when their inputs are synthetic or separately approved for
repository use. Each report must identify its evidence scope precisely. Current scopes include
development-laptop measurements, synthetic/proxy evaluation, mocked-team contract integration, and
static mobile compatibility analysis.

Do not relabel laptop timing as Android evidence. Target-device acceptance requires the actual
tablet, approved FP32 and INT8 models, an approved non-sensitive fixture manifest, and end-to-end
measurement from detected speech end to visible or audible avatar response.

Key non-production reports:

- `openslr127-corpus-evidence.json` records the verified 13,803,410,250-byte OpenSLR 127
  archive SHA-256, safe-extraction counts, complete 89,401-record validation, exact-audio
  duplicate handling, and aggregate speaker-disjoint split evidence. It contains no paths,
  transcripts, speaker identifiers, utterance identifiers, or audio hashes.
- `openslr127-frozen-index.json` freezes the deterministic 510/64/64-speaker
  train/validation/test assignment through per-split index digests. The corresponding private
  record index and speaker assignments remain under ignored local artifact storage.
- `openslr127-source-manifest.json` pins the source URL, CC-BY-2.0 license, archive revision,
  adult-Tamil proxy population, and local-only processing boundary.
- `member2-mocked-three-member-evidence.json` exercises Member 2 between deterministic test-only
  Member 1 and Member 3 adapters; it is contract evidence, not teammate acceptance.
- `proxy-int8-mobile-usability.json` records official ONNX Runtime static graph analysis. It is not
  latency, memory, battery, thermal, emulator, or physical-device evidence.
- `full-track-cpu-smoke.json` records fixture-encoder phoneme-head shape/loss evidence; no gated
  teacher checkpoint was loaded.
- `student-track-cpu-smoke.json` records compact Conformer and Conv-BiGRU distillation-loss smoke;
  no real teacher features were used.
- `dual-track-cpu-comparison.json` records the explicit no-promotion decision and preserves missing
  GPU, accuracy, calibration, quantization, and physical-device gates as `not_measured`.
