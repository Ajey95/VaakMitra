# Private edge deployment

VaakMitra V1 deploys on one supervised GPU workstation. Public Render inference and Vercel-to-Render API rewrites are retired because they conflict with the frozen offline/private boundary in `VAAKMITRA_FINAL_SSOT.md` (DEC-013 and OPS-001..011).

## Topology

```text
Browser on workstation ─┐
Android on private LAN ─┼─ TLS/private LAN ─> FastAPI :8000 ─> local GPU + immutable artifacts
Unity on private LAN ───┘                         │
                                                  └─> local MongoDB; aggregate allow-list only
```

The backend binds to `127.0.0.1` for same-machine use. Bind to the workstation's private interface only when Android or Unity must connect. Do not router-port-forward, tunnel, publish, or expose the scoring endpoint to the internet. Use a local reverse proxy and a locally managed certificate when clients require HTTPS. Firewall rules must allow only the exact therapy-device subnet or device addresses.

## Preflight

1. Read `VAAKMITRA_FINAL_SSOT.md` and `docs/WORD_MODEL_INSTALLATION.md`.
2. Confirm the workstation is encrypted, patched, physically controlled, and synchronized to the local session clock.
3. Confirm NVIDIA driver/CUDA/PyTorch/NeMo compatibility in the frozen model environment.
4. Verify the immutable bundle. Exit code `2` blocks scoring.
5. Set production JWT/admin secrets with the OS secret mechanism. Do not copy `.env.example` values into production.
6. Use exact private origins/hosts; disable `EXPOSE_DEV_CODES`, external TTS keys, Cloudinary, and sync.
7. Start one API worker because the model is GPU-resident.

```powershell
cd D:\VaakMitra-Integrated-Backend\backend
python scripts\verify_artifacts.py --config D:\VaakMitraModels\ta-word-v1\bundle.json --json
$env:APP_ENV = 'production'
$env:VAAKMITRA_DEPLOYMENT_MODE = 'private_edge'
$env:VAAKMITRA_BUNDLE_CONFIG = 'D:\VaakMitraModels\ta-word-v1\bundle.json'
$env:VAAKMITRA_POLICY_MODE = 'deterministic'
$env:VAAKMITRA_SYNC_ENABLED = 'false'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

## Web client

Use the supported Node version declared in `frontend/package.json`, run `npm ci`, test, and build. Serve `frontend/dist` from the same private workstation/reverse proxy so `/api` remains same-origin. The checked-in project has no public-cloud rewrite.

```powershell
cd D:\VaakMitra-Integrated-Backend\frontend
npm ci
npm test -- --run
npm run lint
npm run build
```

## Android and Unity

Point development devices at the workstation's authenticated private-LAN HTTPS origin. The Android emulator may use `http://10.0.2.2:8000/` only during local developer testing. A physical-device release requires an approved private-LAN endpoint and evidence for authentication, microphone teardown, prompt/listen exclusion, cancellation, offline/degraded behavior, and zero forbidden egress. Unity is an avatar/client state machine only; it never owns scoring or unbounded child dialogue.

## Health, canary, and abort

`/health/live` proves only that the API process responds. `/health/ready` includes database status. `/health/scoring` must return HTTP 200 before a scoring-enabled supervised session and HTTP 503 for missing, synthetic, mismatched, unapproved, or unloadable artifacts.

Run the fixed approved adult canary corpus after every restart and record latency/VRAM/output evidence. Abort scoring and use neutral practice if any canary changes, the health endpoint degrades, latency exceeds the approved bound, the device disconnects, or a caregiver/child requests stop. Do not turn an infrastructure failure into RETRY feedback.

## Rollback and evidence

Stop new sessions, preserve aggregate audit records, select the prior immutable bundle, restart, verify, rerun canaries, and record the event. Follow `docs/VERIFICATION_STATUS.md`; unit tests, GPU visibility, HTTP 200 from non-scoring health, or successful frontend build never substitute for model, privacy, physical-device, or clinical proof.
Any topology or exposure change requires an approved SSOT revision before deployment.
