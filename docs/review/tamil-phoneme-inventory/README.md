# Tamil phoneme inventory expert review

This review gate separates an engineering candidate from an expert-approved inventory. Software
can create and validate the packet, but it cannot supply the expert decisions or attestation.

Install the pinned CPU-only transliteration dependency and enable Python UTF-8 mode on Windows:

```powershell
& .\.venv\Scripts\python.exe -m pip install `
  --requirement modeling\inventory\requirements-epitran.txt
$env:PYTHONUTF8 = "1"
```

After OpenSLR materialization, generate the full private lexicon and bounded public review packet:

```powershell
& .\.venv\Scripts\python.exe -m modeling.inventory.generate_corpus_review `
  --records modeling\artifacts\corpora\openslr-127\private\records.jsonl `
  --extract-root modeling\artifacts\corpora\openslr-127\extracted `
  --archive-sha256 <LOCALLY_COMPUTED_ARCHIVE_SHA256> `
  --sources modeling\configs\tamil_phoneme_sources.json `
  --version ta-openslr127-candidate-1 `
  --private-lexicon modeling\artifacts\corpora\openslr-127\private\full-lexicon.json `
  --review-output-dir docs\review\tamil-phoneme-inventory\packet `
  --max-examples 200 --sample-seed vaakmitra-clinician-review-v1
```

The full word lexicon stays private. The review directory contains only the digest-bound candidate,
phone frequencies, bounded isolated-word examples, conflicts/coverage evidence, and a pending
approval template; it contains no corpus path, transcript, speaker ID, utterance ID, or audio hash.

Generate a digest-bound packet from the candidate inventory:

```powershell
& .\.venv\Scripts\python.exe -m modeling.inventory.build_review_packet template `
  --candidate modeling\artifacts\tamil-phoneme-contract.json `
  --output modeling\artifacts\tamil-phoneme-review.json
```

The Tamil linguist, speech-language pathologist, or speech scientist must review every non-blank
token and every proposed allophone mapping. Each row requires `approve`, `reject`, or `replace`
plus a non-empty note. `pending` and `needs_discussion` deliberately block finalization.

The reviewer must also make four explicit policy decisions:

- Whether long vowels remain separate units, represented with the IPA length mark.
- Whether geminates are repeated consonant targets or single phones with duration features.
- Whether only individually reviewed allophone mappings may be applied.
- Whether unseen phones are fail-closed/unscorable or restricted to a research-only unknown unit.

Finally, the reviewer fills in role, organization, UTC review time, and sets
`attests_inventory_reviewed` to `true`. No personal name or contact data is required.

Validate and finalize the completed packet:

```powershell
& .\.venv\Scripts\python.exe -m modeling.inventory.build_review_packet finalize `
  --candidate docs\review\tamil-phoneme-inventory\packet\tamil-phoneme-candidate.json `
  --review docs\review\tamil-phoneme-inventory\packet\approval-manifest.completed.json `
  --output modeling\artifacts\tamil-phoneme-contract.expert-reviewed.json
```

Finalization fails on a changed candidate digest, missing/duplicate rows, unresolved decisions,
unreviewed allophones, invalid replacements, or absent attestation. A successful output records
`expert_approved=true` but intentionally retains `production_ready=false`: child-domain evaluation,
therapist calibration, trained-model evidence, and physical-device validation remain independent
promotion gates.

## Materialized OpenSLR 127 packet

The repository packet was generated from all 89,387 training-eligible records after complete
89,401-record validation and conservative exact-audio duplicate handling. It is bound to archive
SHA-256 `0ec67ad6fc6b5f48aa0f2668722dbdb2642b66c4b49c289c2849ee603f35c8c2`.

Review these files together:

- `packet/token-review.csv`: 60 candidate phone rows.
- `packet/pronunciation-review.csv`: 200 deterministic, isolated-word corpus examples.
- `packet/conflicts-and-coverage.json`: source disagreements, digests, coverage, and privacy flags.
- `packet/approval-manifest.json`: machine-validated token, policy, and reviewer attestation form.

The checked-in manifest intentionally remains `pending_expert_review`. The reviewer should copy it
to `approval-manifest.completed.json`, enter every decision and required note, select all four
policies, and add the UTC reviewer attestation. The original pending template remains immutable
evidence of what was handed to the reviewer.
