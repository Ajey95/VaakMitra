# Veshti reward sticker — 12 November 2026

SSOT3.3.51 / DEC-065 / PRS-008. The existing completion card now contains an original Tamil man in a white/gold veshti, maroon shirt and cooling glasses, with vibhuti and a friendly thumbs-up. A gentle entrance settles to a static sticker. Current-child-name Tamil praise still starts automatically through the existing local speaker and completion ticket; no extra tap or new session screen. Existing four avatars, session routes, Stop/Hear again, quiet controls, Reduced/Still and letter reward opt-outs remain.

The illustration stays visible with its card for readability. It replaces only the old kolam art slot; it does not replace any guide or create a full-screen celebration. Existing captions praise effort, not pronunciation accuracy. Names stay local, with the existing generic fallback when no usable name exists. Offline voice availability is required for sound; text/art remain when unavailable.

## Verification

- 177 JVM tests passed, zero failures/errors/skips. Lint0errors/8warnings. BothABI and instrumentation APK builds passed.
- Physical iQOO I2217/API36:68 native checks passed (19retained +49gallery), including new actual public-completion sticker/automatic-cheer test and normal/2x controls. Native RED on prior8c main failed specifically for missing sticker. Public preview audio is simulated; separate real offline Tamil speaker probe used only public sample name கவின்.
- Voice probe: `accepted=true began=true completed=true unavailable=false`. Callback status is not proof of audible quality, exact name pronunciation or natural playback completion; the inherited probe has a shared terminal callback. No microphone or private child/name recordings collected.
- Four public app-window captures exported and inspected: normal completion,2x compact Rewards,2x effort/Stop and summary. New2x test does not exhaustively assert every full-height caption. The existing full-size2x effort test checks participation feedback/replay and Break/Stop; no all-device layout claim.
- Reconnection follow-up: raw binary transfers failed or changed newline bytes. Four PNGs were retrieved using2KiBbase64chunks and verified against phone-side SHA256 and PNG CRCs. No private recordings/profile files were requested. Pending-review snapshot remains unchanged as history. Emulator fallback had3failed visual attempts (main-thread callback/controls unavailable), so no emulator visual/parity claim is made.
- First retained run passed18/19: larger art put End session below the fold of the existing scrollable letter-break page. The test now scrolls to that same control, clicks it and verifies all3practice marks are saved; final19/19passes. No session/navigation/product source was changed for this correction. End session can require more scrolling on that break page.
- All17 protected avatar/model files unchanged; all12model/reference assets per mainAPK unchanged. Generated PNG transparent alpha and exact decoded pixels verified in each packaged mainAPK. BothABI/test ZIP CRCs and installed ARM/test SHA readbacks match.
- No new emulator runtime parity, first-display/frame-time, audible pronunciation or child-benefit claim. Official V7 remains UNSCORABLE/production_ready=false/approved_for_child_scoring=false.

## Frozen artifacts

ARM SHA256: `195ee225d45bd7eb51370b9115af594df06f11dc2afb57b14aca20b8ed0cbe9e`.

x86 SHA256: `130ca6b68a1722dec9c9e4419fe4a2f1da738e2a2d0e06a12dbd3206b9d2dfd6`.

Test SHA256: `68edd233d2b7acfdaf3a71c08a468e8a344c737ed821672f4e3f4fe09fb13ddf`.

Frozen APKs: C:/Users/AJEYA/VaakMitraArtifacts/veshti-reward-20261112. Source/evidence/manifest: D:/VaakMitraData/deliveries/veshti-reward-20261112. Analysis: D:/VaakMitraData/analysis/veshti-reward-20261112. Artwork: SpeakEasyAndroid/app/src/main/res/drawable-nodpi/vm_reward_veshti_man.png, SHA256 `624071d83d89153f077ec282c797eeb7372fddfafbe2fc2a76be4e2ab86c60a5`. Built-in image_gen used; full final prompt/source/hash at docs/evidence/veshti-reward-20261112/artwork-provenance.json. Original generated pixels/alpha preserved, no replacement of avatar assets. No celebrity performance/film clip or clinical-evidence claim.

## Review and limits

One fresh scoped review found no Critical/Important issues. Deferred Minors: new2x test covers compact preview rather than every full completion caption; system-animation snapshot refreshes on resume; source PNG decodes to about6MiB, first-display timing unmeasured. Source speech/name/ticket/mic/score behavior is unchanged. Current public UI tests use inert fixtures and do not establish private-session audible E2E, child comfort or therapy effectiveness.

Existing dirty branch codex/backend-verification-lab and HEAD712de54ee568da6262131f06092c0d4d251b2c92 preserved, no commit/merge/push/cleanup. Prior guide ARM8c1adccd3c499235a171ff732c3f1714ae7c972ffc6bee7af2ce3782261ae7b9 remains frozen at C:/Users/AJEYA/VaakMitraArtifacts/guide-liveliness-20261112/app-arm64-v8a-debug.apk as verified rollback. Protected roots unchanged; no dependency, training, dataset or cloud runtime/spend change.
