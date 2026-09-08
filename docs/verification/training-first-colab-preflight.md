# Training-first Colab preflight and recovery

Use this checklist for the `deadline_7day` run. Do not start the long stage until every preflight
item is satisfied. The output is an adult Tamil engineering proxy with production ready false; it
is not child or clinical validation.

## Inputs and account gates

1. Push the intended VaakMitra branch or commit so Colab can fetch it. Record the exact
   40-character Git commit shown by the repository cell.
2. Upload `modeling/artifacts/colab/vaakmitra-colab-private-metadata.zip` to
   `/content/drive/MyDrive/VaakMitraGPU/inputs/`.
3. Upload `mile_tamil_asr_corpus.tar.gz` to the same folder, or explicitly permit the pinned
   resumable download. The notebook must verify 13,803,410,250 bytes and the frozen SHA-256.
4. Accept the gated AI4Bharat model conditions. Add `HF_TOKEN` only through Colab Secrets.
5. In Colab, select a GPU runtime. Prefer a runtime with at least 24 GB VRAM for the adaptive
   stages; GPU availability and session duration are not guaranteed by a Pro subscription.
6. Confirm the runtime has enough local disk for the archive, 17,314,415,289 extracted bytes, and
   the 10 GiB working reserve.

## Launch sequence

1. Open `notebooks/VaakMitra_GPU_Training_Colab.ipynb` from the pushed revision.
2. Confirm `TRAINING_PROFILE_NAME="deadline_7day"` and set `VAAKMITRA_REPOSITORY_REF` to the pushed
   branch or exact commit.
3. In `Runtime > Change runtime type`, select runtime version `2025.07` and a GPU. Reconnect and
   run `configuration`, then `environment`; the environment cell requires native Python 3.11.
4. Verify the detached repository commit and clean-tree checks before proceeding.
5. Run through `gpu-canary`. Do not start `reference-head-training` until the report below passes.

| Gate | Required value |
|---|---|
| Notebook commit | exact 40-character Git commit recorded in run manifest |
| GPU | detected and recorded; no guaranteed model assumed |
| Canary duration | at least 1,800 seconds unless smoke profile |
| Mid-epoch resume | passed |
| Non-finite loss | zero events |
| Head-only projected finish | fits remaining deadline budget |
| Checkpoint | numbered file, sidecar size, and SHA-256 all verify in Drive |
| Inventory | expert reviewed, or provisional research-only flag recorded |
| Unknown phones | at most 0.05 of eligible plus unknown records |
| Evidence ceiling | adult Tamil engineering proxy; production ready false |

## Reconnect and recovery

After a Colab preemption, reconnect and rerun from the configuration cell. Use the same repository
commit, profile, archive, corpus index, inventory, and teacher checkpoint. The engine loads the
newest compatible verified checkpoint and resumes at the next unapplied optimizer boundary. Do
not bypass a binding or batch-order mismatch. If a Drive checkpoint write fails, preserve the
local checkpoint and copy it only after size and SHA-256 verification.

If `diagnostic-failure.json` reports a non-finite loss or gradient, stop that stage and retain its
sanitized evidence. For CUDA OOM, allow only the bounded frame-budget reduction; a repeated OOM
ends the stage. Do not change the split, thresholds, or inventory to make a run pass.

## Required handoff artifacts

Inspect and retain `run-manifest.json`, `teacher-probe.json`, `canary-report.json`,
`reference-metrics.json`, `reference-artifact-head-only.json`,
`reference-artifact-manifest.json`, `reference-evidence.json`, `artifact-hashes.json`, and
`vaakmitra-gpu-results.zip`. Retain the selected native checkpoint and its SHA-256 sidecar
separately from the result ZIP. Student files are optional under the deadline profile and must not
block a complete adult-reference evidence bundle.
