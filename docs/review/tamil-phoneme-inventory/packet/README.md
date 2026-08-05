# OpenSLR 127 Tamil clinician review packet

This packet is a bounded, corpus-backed handoff generated from the locally verified OpenSLR 127
Tamil archive. It contains isolated-word examples and aggregate evidence only; it contains no
audio, full transcript, corpus path, speaker ID, utterance ID, or audio hash.

## Reviewer workflow

1. Complete every row in `token-review.csv` with `approve`, `reject`, or `replace`; add a note for
   each decision and a replacement token where applicable.
2. Complete every row in `pronunciation-review.csv`; use `corrected_ipa` when rejecting or
   correcting a proposed pronunciation and explain the decision in `notes`.
3. Copy `approval-manifest.json` to `approval-manifest.completed.json`. Mirror the final token
   decisions, resolve the vowel-length, gemination, allophone, and unknown-phone policies, and add
   the reviewer role, organization, UTC review time, and truthful attestation.
4. Run the fail-closed finalizer from the repository root:

```powershell
$env:PYTHONUTF8 = "1"
& .\.venv\Scripts\python.exe -m modeling.inventory.build_review_packet finalize `
  --candidate docs\review\tamil-phoneme-inventory\packet\tamil-phoneme-candidate.json `
  --review docs\review\tamil-phoneme-inventory\packet\approval-manifest.completed.json `
  --output modeling\artifacts\tamil-phoneme-contract.expert-reviewed.json
```

Finalization rejects missing decisions, missing notes, unresolved policies, changed candidate
digests, incomplete token coverage, invalid replacements, non-UTC review times, and absent or
false attestation. Even a valid expert-reviewed output remains non-production until the separate
child-domain, therapist-calibration, trained-model, and physical-device gates pass.

## Frozen packet identity

- Archive SHA-256: `0ec67ad6fc6b5f48aa0f2668722dbdb2642b66c4b49c289c2849ee603f35c8c2`
- Candidate digest: `2014432f30b4b41dd1a1c557b8982cef7d5f0f1394e685f769f0054d73e8fba9`
- Lexicon digest: `2e16c7e31ee8293275f952aded04b5a358f5e3dbc3538c8f68333c9279b21dd6`
- Review packet digest: `4d9466d8001307fb3b709cb65ed569070236def1c3b7288fc2b9ac057b4c2695`
- Candidate tokens requiring review: 60
- Corpus-backed pronunciation examples: 200
