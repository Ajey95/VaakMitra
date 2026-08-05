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
  --candidate modeling\artifacts\tamil-phoneme-contract.json `
  --review modeling\artifacts\tamil-phoneme-review.completed.json `
  --output modeling\artifacts\tamil-phoneme-contract.expert-reviewed.json
```

Finalization fails on a changed candidate digest, missing/duplicate rows, unresolved decisions,
unreviewed allophones, invalid replacements, or absent attestation. A successful output records
`expert_approved=true` but intentionally retains `production_ready=false`: child-domain evaluation,
therapist calibration, trained-model evidence, and physical-device validation remain independent
promotion gates.
