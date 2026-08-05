# Benchmark reports

Generated JSON reports belong here only when their inputs are synthetic or separately approved for
repository use. Each report must identify its evidence scope precisely. Current scopes include
development-laptop measurements, synthetic/proxy evaluation, mocked-team contract integration, and
static mobile compatibility analysis.

Do not relabel laptop timing as Android evidence. Target-device acceptance requires the actual
tablet, approved FP32 and INT8 models, an approved non-sensitive fixture manifest, and end-to-end
measurement from detected speech end to visible or audible avatar response.

Key non-production reports:

- `member2-mocked-three-member-evidence.json` exercises Member 2 between deterministic test-only
  Member 1 and Member 3 adapters; it is contract evidence, not teammate acceptance.
- `proxy-int8-mobile-usability.json` records official ONNX Runtime static graph analysis. It is not
  latency, memory, battery, thermal, emulator, or physical-device evidence.
