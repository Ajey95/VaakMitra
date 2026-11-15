# Focused words and phoneme model update — 12 November 2026

The updated debug app is installed on the iQOO and emulator. It contains **25 words**, with a default **18-word focused view** and an **All words** view. The additions are என்ன (Enna), நான் (Naan), இது (Ithu), எனக்கு (Enakku), கை (Kai), and வீடு (Veedu), appended at routes 20–25. The original 19 routes, 247 letter levels, avatars, Tamil theme and session/privacy behavior are preserved. Phoneme results offer voluntary **Next word**, **Practise again**, and **End session**; advancing does not mark pronunciation correct.

## Model outcome

**V7 remains deployed. Neither new training configuration qualified.** The additional word lessons are experimental practice additions, not proven recognition improvements. Retained V7's new-six calibration PER is 51/93 phones (54.84%, only 23 clips), so recognition of those additions remains unreliable. Historical 75/540 = 13.89% PER applies only to the previously exposed old-19 adult evaluation subset; it is not a new result or child accuracy claim.

Both configurations improved some new-word calibration results while regressing old words and broader speech. The strict nonregression gates were preserved, no candidate was selected, and no candidate evaluation-set inference occurred. Table entries show the best focused-calibration epoch descriptively, not a deployment choice. Baseline: focused18 73/400, old19 31/547, new6 51/93, broader 6864/12413. These groups overlap and their counts are not additive.

| Control | Epochs completed | Best focused epoch | Focus18 edits/phones | Old19 edits/phones | New6 edits/phones |
|---|---:|---:|---|---|---|
| balanced75 | 7 | 6 | 47/400 | 56/547 | 20/93 |
| frozen80 | 1 | 1 | 67/400 | 38/547 | 43/93 |
| frozen80-recovery | 7 | 7 | 51/400 | 56/547 | 23/93 |

The original frozen80 process exited after one epoch during concurrent JVM native-memory exhaustion; the exact training exit cause was unconfirmed. One restart repeated the same configuration/seed, reproducing its first loss and all edit counts exactly. No additional hyperparameter search, relaxed thresholds, or evaluation-based reselection occurred.

## Data and resources

The frozen run contains 18,214 rows, with 2,194 focused training clips including 250 for the six additions. Eighty complete original Enna recordings were added after source/duration/mono/RMS/clipping checks; prepared one-second crops were not substituted. Existing splits were retained. The cache contains 86 focused calibration clips (23 new-six) and 99 focused evaluation clips (34 new-six); additional audit-only Enna holdouts were not used. Public-adult phone labels and speaker IDs remain provisional. No child recordings were supplied or used.

The existing 3.48 GB cache was reused through mmap; a 15.36 MB sidecar holds the added waveforms. Local RTX4060 Laptop 8 GB training used batch64, four CPU threads, AdamW, dropout0.2 and frozen BN statistics. Balanced75 used 75% focus sampling with encoder/head LR2e-6/2e-5; frozen80 used 80% focus and head LR1e-5. Word/speaker balancing and shift/noise/echo augmentation were used; caps were 30 epochs, patience7, and 12 minutes per control. Reported training-loop wall time, including calibration and interrupted work, was **711.329 seconds (11.86 minutes)**. Peak allocated CUDA memory was 222,592,000 bytes. Heavy build/training concurrency exhausted host memory; the successful build used one worker and a 1 GB heap. Cloud GPU spend was **₹0**; local electricity was not metered. No cleanup was performed.

Robustness used **86 source clips from 74 distinct utterances**, plus **430 deterministic derivatives**. Focused calibration PER was clean18.25%, noise20dB20.25%, noise10dB23.50%, echo27.75%, lowpass20.00%, and quiet18.25%. Derivatives are correlated public-adult calibration checks, not independent tests or child simulations. Original source IDs/hashes and all metrics remain in the frozen experiment.

## Review and verification

One fresh AI review identified five Important issues; a source-count reporting error was also regraded Important. One fix pass addressed all six: voluntary word progression, source/PCM digest separation and all MSWC reservations, consumer cache revalidation, separate hash-bound 25-word provisional references, atomic/recoverable finalization, and honest source cardinality. No second review or deferred minor finding. The retrospective audit checked all 80 additions against 348 reserved MSWC rows, including 23 Enna holdouts, plus base/audit identities and canonical PCM: **no collision**. The full parent cache digest remains unchanged. Historical data/scripts/intents were not rewritten; pre-fix sources are archived separately from the hardened current code.

Final checks: **504 backend tests; 110 Android JVM tests; lint 0 errors/7 warnings; both APK ABIs and test APK built; emulator 33 native tests (19 retained/model/reference +14 gallery); iQOO 5 public-audio/reference tests**. Native tests exercise actual VAD, identical predictions across all six new target IDs, installed reference hashes/inventory, focused retry/2→13 progression/25→summary, enlarged text and inert public capture. No private microphone, camera, account writes or uploads were used. App-window screenshots were inspected. Both installed packages were read back and SHA verified; MainActivity was reopened.

All ten retained V7 model assets are byte-identical to the previous APK. The separate practice reference bundle contains all 25 provisional sequences and never enters decoder inputs. The model remains 61 tokens, 16kHz mono/3seconds, 75 frames/40ms, unconstrained beam5/top8. ONNX SHA256: 94c30918c5be357d7384ddc6dd39fb65ed16ae80a507699b649332c049885683.

Final installed APK SHA256:
- ARM64: bd6bd7275254a5cf73f78d04a85ec41b5a63a1b905fd02990116b300d5241834
- x86_64: f7e9bb8b1893a6eca40028eadac85c0de2aeeb4b2113ab3b14eb49678120441c
- Test: 67fb7c1e19fa03e6b9eea05ee2c1531595d188fa72fbc8b565d6fed6950d47ce

## Limits and handoff

Official results remain **UNSCORABLE**, production_ready=false and approved_for_child_scoring=false. Backend intended catalogue is now104/v1.1.0, original100 unchanged, four additions pending review. Old1.0 plans explicitly fail the existing version guard; no live backend, database migration or store release was performed. This is a debug review delivery, not clinically validated child pronunciation assessment.

SSOT3.3.42 DEC-058; branch codex/backend-verification-lab HEAD712de54 unchanged. No commit, merge, push or cleanup. Protected roots read-only. Repo: D:/VaakMitra-Integrated-Backend-Lab. Frozen run: D:/VaakMitraData/artifacts/phoneme-focused25-20261112-v2. Evidence: D:/VaakMitraData/analysis/focused-words-20261112. Delivery: D:/VaakMitraData/deliveries/focused-words-20261112. Source archive contains scoped updates, not a standalone project. Full review/rulings and verification evidence are included.
