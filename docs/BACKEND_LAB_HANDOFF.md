# Backend verification lab — 2026-09-12

Authority: `VAAKMITRA_FINAL_SSOT.md` v3.3.4, especially DEC-012/018/022/023/024/025, DLA-001..006, UX-002/003/008, SES-006, GOV-001..007 and GATE-01..06. Isolated worktree: `D:\VaakMitra-Integrated-Backend-Lab`, branch `codex/backend-verification-lab`. Protected research/source repositories remain untouched.

## Guide-review check — 2026-09-15

Use `http://127.0.0.1:5173/dev/backend-lab` for the **adult engineering demonstration**. After opening the local test session and selecting a word, click **Start live practice** once. Pippin prompts the Tamil word, opens the microphone only after the prompt ends, stops after speech plus trailing silence (or seven seconds), runs the real adult diagnostic, and either praises, asks for recapture, or automatically coaches a selected written chunk and the whole word before listening again. The red **Stop live practice** action cancels prompt/capture/inference and releases the microphone. Manual microphone and adult WAV paths remain available. The live response exposes the target, leading model candidate, capture duration/quality, raw and normalized ASR evidence, classifier evidence, reference similarity, the adult index, and an actionable development result: MATCH, TRY AGAIN, UNCERTAIN — RETRY, or RECORD AGAIN. It explicitly says a candidate is not a pronunciation diagnosis and gives no child score. The right-hand PASS/RETRY contract examples remain static simulations, unrelated to the live attempt.

For a repeatable file demo, choose `மீண்டும்` (`TA_WORD_0096`) and the public adult evaluation fixture `D:\VaakMitraData\prepared\openslr127-word-v1\train\ISTL_0000209_0000058\00.wav`. The fixture produces a leading `மீண்டும்` candidate, real VAD/ASR/classifier/DTW values, adult index `1.0`, and development result MATCH. Selecting `அம்மா` (`TA_WORD_0001`) while submitting the same WAV demonstrates retry/uncertain chunk remediation. Silence demonstrates RECORD AGAIN. The real browser and loopback verifiers passed; 12/12 isolated session checks passed. Full backend Pytest collected 374 tests; frontend Vitest passed 225 tests, full Playwright 59/59, ESLint, and Vite build passed using bundled Node v24.19.0. The default shell's unsupported Node v21.7.1 fails in Rolldown before tests run; use the bundled Node path below.

This is **not yet an Android/mobile edge deployment**. The installed diagnostic model runs via the development API on this host; no quantized INT8 student or mobile ONNX bundle was found in the workspace. The legacy Android code still calls the remote speech endpoint, so it must not be presented as on-device inference. Verbal clinician permission for this private guide review does not change calibration metadata or establish child-separated validation. Child testing and any clinical approval record remain separate future evidence.

## Current local website result — 2026-09-14

The internal website is at `http://127.0.0.1:5173/dev/backend-lab`; the API is at `http://127.0.0.1:8002`. The adult operator lab now displays a separate provisional match index while the official result remains `UNSCORABLE` with a null decision probability. The launcher defaults to the hash-checked r4 adult engineering rebuild. A real HTTP run of the public adult evaluation-split WAV `D:\VaakMitraData\prepared\openslr127-word-v1\train\ISTL_0000209_0000058\00.wav` for `மீண்டும்` returned ONNX VAD plus ASR/classifier/DTW evidence, `adult_preview.status=provisional`, `adult_preview.estimate=1.0`, and `persisted=false`. That saturated index is **not** measured accuracy or a validated child score. Silence produced no estimate; 12/12 isolated synthetic MongoDB session checks passed. There is no public or child release claim.

## Review-day live run — 2026-09-14

The repeatable local demo is running at `http://127.0.0.1:5173/dev/backend-lab` with the API on `http://127.0.0.1:8002`. It is loopback-only and uses the completed, **unapproved adult engineering** evidence directory `D:\VaakMitraData\artifacts\live-rebuild-2026-09-12-r4`; it is not a consumer/mobile deployment. If either service has stopped, use the two launch commands below. Allow the Tamil model several minutes to load before testing audio.

Demonstration: click **Run live check**; the process and database should show `200`, while production scoring should show `503 / bundle_config_unavailable` (the expected safe gate). Check the adult/synthetic-audio declaration, click **Open local test session**, and confirm `Model: ready`. Choose a word and click **Record adult mic**. Allow microphone access in the browser, speak the selected word, then click **Stop & test** within seven seconds. The browser encodes a short mono PCM WAV in memory, stops the microphone, and posts it to the same isolated adult diagnostic endpoint as file upload. **Cancel recording**, **Stop / clear audio**, and **Close test session** release capture; canceled audio is not submitted. The original adult WAV upload remains optional: choose `மீண்டும்`, select `D:\VaakMitraData\prepared\openslr127-word-v1\train\ISTL_0000209_0000058\00.wav`, and click **Run real audio test** for a reproducible reference. The model runs ONNX VAD, ASR, classifier, and reference similarity. The lab displays a separate provisional adult index when the evidence gates allow it; the official decision remains `UNSCORABLE / CALIBRATION_UNAVAILABLE` with no correctness probability. The right-hand PASS/RETRY selector is explicitly **simulated** and makes no backend call. The authentication/vocabulary boxes can show authentication required unless a separate admin account is signed in; that does not disable the isolated local adult-audio test.

Fresh evidence: `/health/live` and `/health/ready` returned 200; the diagnostic runtime reported 19 engineering words, `device=cuda`, `vad_mode=onnx_cpu`, `pipeline_ready=true`, and `scoring_ready=false`. `scripts/backend/verify_local.py` exited 0: real local MongoDB, operator auth, 100-word catalog, 12/12 synthetic lifecycle checks, repeatability, silence rejection, and the checksum-bound public adult WAV all passed. The adult response included ASR/classifier/DTW evidence and `UNSCORABLE / CALIBRATION_UNAVAILABLE`. A separate real Edge browser flow loaded the page, opened the diagnostic session, uploaded that WAV, and rendered the result without page errors; the 390-pixel viewport had no horizontal overflow. This is engineering evidence only, not child accuracy, clinical approval, or mobile-device performance.

## Start and test

The installed WSL NeMo environment, MongoDB binary and engineering artifacts are used; no Docker, cloud, or model download is needed at launch.

```powershell
wsl -d Ubuntu-24.04 -- /home/vab/.local/share/vaakmitra/venv-py310/bin/python -u /mnt/d/VaakMitra-Integrated-Backend-Lab/scripts/backend/run_local.py
```

The launcher defaults to the verified r4 adult rebuild. To override it with another completed adult evidence directory for local diagnostics only, set it explicitly for the WSL process (replace the placeholder with the actual WSL path):

```powershell
$evidence = '/mnt/d/path/to/completed-rebuild-directory'
wsl -d Ubuntu-24.04 -- env "VAAKMITRA_ENGINEERING_EVIDENCE_DIR=$evidence" /home/vab/.local/share/vaakmitra/venv-py310/bin/python -u /mnt/d/VaakMitra-Integrated-Backend-Lab/scripts/backend/run_local.py
```

The runner requires non-empty `calibration.json`, `evidence.jsonl`, `provenance.json`, and `report.json`, checks their hashes and unapproved adult-only metadata, then recomputes diagnostic artifact hashes. An incomplete or approved directory is rejected before MongoDB startup. This switch never approves calibration or changes production scoring readiness.

In a second PowerShell terminal:

```powershell
cd D:\VaakMitra-Integrated-Backend-Lab\frontend
$env:VAAKMITRA_DEV_API_TARGET = 'http://127.0.0.1:8002'
& 'C:\Users\AJEYA\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Open [the lab](http://127.0.0.1:5173/dev/backend-lab). Run the health check. Confirm adult/synthetic-only testing, then open a local test session. Model loading can take several minutes; refresh its status until ready. Choose a Tamil word and record an adult microphone attempt, or use the optional adult PCM WAV input. Microphone permission is requested only after **Record adult mic** is clicked. Loopback HTTP is a browser secure context; a remote non-HTTPS copy of this page cannot use the microphone. A reproducible public adult fixture for மீண்டும் is:

`D:\VaakMitraData\prepared\openslr127-word-v1\train\ISTL_0000209_0000058\00.wav`

Run session checks to exercise isolated synthetic records in real MongoDB. Those temporary databases are removed by the scenario runner; no child records are created or deleted. Stop/clear drops the browser's selected audio/result. An in-flight model computation remains occupied until it finishes and cannot be overlapped by another request.

The local operator capability is a short-lived, HttpOnly, SameSite=Strict cookie restricted to the diagnostic namespace. It is not a child account, therapist approval, or general administrator login. Diagnostic routes require explicit development mode and loopback requests, and are disabled by default/rejected in production.

## Repeatable verification

```powershell
wsl -d Ubuntu-24.04 -- /home/vab/.local/share/vaakmitra/venv-py310/bin/python -u /mnt/d/VaakMitra-Integrated-Backend-Lab/scripts/backend/verify_local.py
```

This verifies real administrator authentication, the 100-word protected catalog, real database lifecycle checks, public adult audio checksum, ASR/classifier/DTW evidence, CPU ONNX VAD, correct-target `DEV_MATCH`, wrong-target remediation, silence `DEV_UNAVAILABLE`, repeated-audio stability, no child persistence, and capability revocation. It waits through bounded API and cold-model startup but fails if readiness never arrives. Credentials are generated in an owner-only WSL runtime directory and are never printed. MongoDB listens only on WSL loopback port 27018; API is loopback port 8002. This launcher is development infrastructure, not a consumer-mobile deployment.

To check the visible page against the actual running model (not a mocked browser route), run from `D:\VaakMitra-Integrated-Backend-Lab\frontend`:

```powershell
& 'C:\Users\AJEYA\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' scripts/verify-live-lab.mjs
```

The 2026-09-15 run exited 0 and verified correct-target MATCH without remediation, wrong-target retry/uncertain with two chunk-and-blend cycles, enforced break, clear-audio, and session close in Chrome. A separate browser test drives the microphone UI with injected synthetic PCM, verifies a WAV-only diagnostic POST, and checks track release on submit, cancel, close, and audio-graph setup failure. Missing speech produces RECORD AGAIN with no estimate. These checks prove the adult development interaction and transport; they do not measure child or clinical accuracy.

## Implemented fixes

- SES-001..005: one open session per child, explicit plan limits, atomic attempt claims, total-capture limits, lifetime including pauses, retry breaks, adult resume/switch, pause/stop, expired inference leases, and bounded safe summaries.
- Retired plans preserve history; former therapists lose summary access after reassignment.
- MOD-008: bounded database reconnects, serialized reconnect admission, explicit readiness, corrected PyMongo TLS-option behavior.
- DEC-018/PRV-002: real-artifact adult diagnostics separated from all child-plan routes, upload limits, memory-only multipart parsing (including valid uploads above Starlette's 1 MiB spool threshold), origin/capability protection, and production disablement.
- SES-001: legacy unbound speech assessment rejects requests instead of bypassing plan/session limits.
- MOD-003/PRV-002: NeMo receives audio arrays, not temporary WAVs; eval mode is restored before and after transcription, including error paths. NeMo's teardown unfreezes encoder/decoder into training mode unless corrected.
- AU-007..011: real local Silero ONNX CPU VAD, per-capture state reset, 700 ms pause merge, artifact/config integrity and calibration binding; no energy-only production PASS.
- CLS-004/MOD-008: missing classifier classes and engineering bundles cannot be promoted to production scoring.

## Evidence and limits

Real development smoke testing exercised the 19-word engineering artifact bank (929 references), not all 100 intended words. The public adult clip executes ONNX VAD, both ASR views, classifier and reference DTW. Calibration remains unapproved, so the correct result is `UNSCORABLE / CALIBRATION_UNAVAILABLE`, with no correctness probability. This verifies executable integration, not accuracy.

The older worktree extractor calls transcription and can be affected by NeMo teardown, while the protected main checkout has a newer embedding-only extractor that is not automatically proven affected. The corrected-VAD exact-live adult engineering rebuild is now `D:\VaakMitraData\artifacts\live-rebuild-2026-09-12-r4`; use its WSL path in the explicit environment switch above. The old artifact was not overwritten or approved. This adult-only rebuild does not settle legacy embedding provenance or provide full vocabulary coverage, approved canaries/clinical review, child-separated validation, student training/quantization or physical Android evidence. These remain release gates, not replaced by test fixtures or a working UI.

The inherited word-therapy frontend now uses authenticated assigned plans and the canonical guarded session API, with server-owned progress, cancellation, Pause/Stop and safe unavailable states. Visual letter teaching remains silent and unscored. Scoped review passed; frontend213unit tests and7single-worker synthetic Edge scenarios pass. Real bcrypt/JWT-cookie and MongoDB ASGI HTTP checks verified plan isolation and fail-closed lifecycle with synthetic accounts, not real child scoring. The mock backend lab remains isolated; these checks are not evidence that every inherited product page works.

With the r4 bundle explicitly selected, the loopback smoke checker completed real adult inference and all 12 temporary real-Mongo lifecycle scenarios. The public adult clip produced ASR, classifier, DTW and ONNX VAD evidence but correctly returned `UNSCORABLE / CALIBRATION_UNAVAILABLE`, with no decision probability, because this engineering calibration is not approved. This is a local integration result, not a child or mobile-device validation result.

The public ONNX VAD was obtained from [Silero VAD](https://github.com/snakers4/silero-vad), MIT license, commit `867c2aa692646a1f1de3e94a15c9dd9f614c0acb`; SHA-256 `1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3`. ONNX Runtime is pinned to 1.22.1. MongoDB 8.0.32 archive was verified against its published SHA-256. Raw audio remains local; the local FastAPI harness is not the eventual on-device Android runtime.

See `BACKEND_COMPLETION_CONTEXT.md` for current verification counts and remaining work. No claim of 100% clinical/production readiness is made.
