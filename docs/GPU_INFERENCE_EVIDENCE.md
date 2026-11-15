# RTX 4060 model smoke evidence

Evidence date: 2026-09-06. Scope: local engineering smoke only. This is not a production-bundle approval, performance benchmark, child-speech accuracy result, or clinical claim.

## Frozen runtime and artifacts

- Host GPU: NVIDIA GeForce RTX 4060 Laptop GPU, 8,188 MiB, driver 592.82.
- Runtime: WSL2 Ubuntu 24.04, Python 3.10.21, PyTorch 2.3.1+cu121, CUDA runtime 12.1, AI4Bharat NeMo 1.23.0rc0.
- AI4Bharat NeMo source revision: `8dce88cf8e94963e2033c3137f7b9993b51db88a`.
- Tamil checkpoint: `D:\VaakMitraModels\ta-word-v1\upstream\indicconformer_stt_ta_hybrid_rnnt_large.nemo`.
- Checkpoint SHA-256: `40a6fce3374ceb67daa2a071e92f0948c51c6a95b734d4881a3bcfe0b1bed32a`.

## Positive-control fixture

The labeled adult Tamil fixture is Google FLEURS `ta_in` development item `1136908823578381036`, obtained from `google/fleurs` on Hugging Face. The upstream float WAV was converted to mono 16 kHz PCM16 outside the repository so it exercises the backend's accepted WAV contract.

- PCM fixture: `D:\VaakMitraRuntime\fixtures\google-fleurs-ta-in\selected\dev\1136908823578381036-pcm16.wav`.
- PCM fixture SHA-256: `ea33059e518cbb182c9a11692097775c12d17150b594866cec3260ef6d2f021f`.
- Duration: 5.46 seconds.
- Reference: `இந்த பருவத்தின் முதல் நோய் பற்றிய தகவல் ஜூலை இறுதியில் பதிவு செய்யப்பட்டது`.

## Observed end-to-end result

The production `decode_wav_bytes` path accepted the fixture, `NeMoIndicConformerAdapter` verified and restored the checkpoint on `cuda:0`, extracted encoder representations, and ran Tamil CTC decoding.

- Transcript: `இந்த பருவத்தின் முதல் நோய் பற்றிய தகவல் ஜூலை இறுதியில் பதிவு செய்ய பட்டது`.
- Exact-reference proxy: `0.0`, correctly reflecting the spacing difference between `செய்யப்பட்டது` and `செய்ய பட்டது`; this proxy is not a calibrated score.
- Embeddings: shape `[137, 512]`, `float32`, all finite.
- Cold checkpoint restore: 119.467 seconds.
- Inference after restore: 2.320 seconds.
- Peak CUDA memory allocated: 687,356,416 bytes.
- Peak CUDA memory reserved: 767,557,632 bytes.
- Machine-readable evidence: `D:\VaakMitraRuntime\evidence\2026-09-06-gpu-inference.json`, SHA-256 `5f43e34105f468b8dd8f025b2eeae5b1ffaf61be9f75181c618fd72cef3ceb67`.

The first live probe exposed that this AI4Bharat NeMo fork returns a nested transcription structure. The adapter previously treated the nested list as a hypothesis object and discarded its text. A regression test now covers the observed return shape, and the minimal parser fix recurses through list/tuple containers.

## Governed embedding-shard canary — 2026-09-07

The same checkpoint and adult FLEURS fixture were run through `scripts/model/extract_embeddings.py` in the pinned WSL environment at `/home/vab/.local/share/vaakmitra/venv-py310`. This verifies the new resumable shard boundary in addition to the model adapter.

- Model load: 131.937 seconds.
- Inference and shard write: 2.573 seconds.
- Stored embedding: `[137, 512]`, finite `float32`.
- Model SHA-256: `40a6fce3374ceb67daa2a071e92f0948c51c6a95b734d4881a3bcfe0b1bed32a`.
- Vocabulary SHA-256: `ac156b426c85fe6f91c47ae22c6d468d724b717fd4a731a382e73e0c265b38eb`.
- Source manifest SHA-256: `482d8aa265697b186653dd6e865911071a7df8cbb07146d7bd41a2d18d8fb97b`.
- Shard manifest SHA-256: `dc557a1141878b49899c1540b7ec0041d1e82269093cabe789b507accd7e91ed`.
- Shard file SHA-256: `fd3a2a9344826566c78d5f4edeb0315a7b8c690fc4ea96f19242739db154b508`.
- Report: `D:\VaakMitraData\embeddings\fleurs-canary\report.json`, SHA-256 `014eed3e3615e5d5f171733c1b3d253528b3dc3cacf6a54123610031933209a0`.
- Peak CUDA allocation/reservation: 687,356,416 / 767,557,632 bytes.

The source is a sentence-level `OTHER` canary with unavailable speaker identity. It proves extraction integrity and resumability only; it is not eligible for a target reference bank.

## Full MLCommons `OTHER` embedding extraction — 2026-09-07

All 1,841 accepted, speaker-disjoint MLCommons Tamil clips were processed by the same hash-pinned checkpoint and WSL GPU runtime. The result is 29 validated immutable shards under `D:\VaakMitraData\embeddings\mswc-ta-other`; every shard was reopened with `allow_pickle=false`, its internal manifest hash checked, and all 1,841 unique sample IDs reconciled.

- Source/prepared manifest SHA-256: `b665337bebda6a7c6048861507c95396a4d2f4f855e798abfa459329a8cda80a`.
- Model SHA-256: `40a6fce3374ceb67daa2a071e92f0948c51c6a95b734d4881a3bcfe0b1bed32a`.
- Vocabulary SHA-256: `ac156b426c85fe6f91c47ae22c6d468d724b717fd4a731a382e73e0c265b38eb`.
- Model load: 130.700 seconds; extraction: 565.720 seconds.
- Peak CUDA allocation/reservation: 683,723,264 / 734,003,200 bytes.
- Report SHA-256: `2ebda6d6b6b2dd3ee23887ff32975a7e0a4594293e54344aedc0ea5ae329bf1e`.
- First/last shard SHA-256: `a11b1f27a1fc64816c4b7b756c9f642f600126917bfa03704c1b35fff38f8cd7` / `7f4304c010557bdca63ca79bba9e1c9bf4ee53a08f33be7a5dbff9917d5ea120`.

These are valid `OTHER`/confusable embeddings, not target examples. They do not permit a classifier fit because the release gate requires active target classes and at least 10,000 accepted `OTHER` examples.

The complete OpenSLR 65 sentence corpus was normalized separately (4,264 accepted of 4,291), but whole-sentence embeddings were deliberately not generated for the word classifier. Those recordings must first be forced-aligned into reviewed word clips; otherwise sentence duration and context would create a misleading negative class for a word-level task.

## Remaining release gates

This evidence proves local checkpoint integrity, CUDA restoration, encoder execution, non-empty Tamil decoding, and a complete resumable extraction pass over the currently accepted word-level MLCommons corpus. It does not satisfy the approved-bundle gate. Active target classes, a trained closed-vocabulary classifier, approved reference bank, child-separated calibration, consented startup/release canaries, target-child accuracy, privacy packet capture, physical Android/Unity loop, clinician approval, and rollback rehearsal remain pending. The extraction throughput is not an interactive API latency benchmark.
