# Validation evidence still required

Authority: SSOT DATA-001..013, GATE-03/GATE-06. This is a project release checklist, not a claim that validation has passed.

The implemented human-review APIs, signed packet workflow, and 14-day checkup behavior are documented in `docs/GOVERNANCE_REVIEW_HANDOFF.md` (DEC-019, GOV-001..007, CHK-001..004). The 1,565-row local reference packet is candidate-only and has no approved entries. Backend/frontend automated tests can establish implementation behavior, not consent, independent ratings, child accuracy, or physical-device readiness.

## What is currently available

- Public adult corpus: 15,972 machine-reviewed segmented clips, including 14,033 OTHER clips; 83 of 100 intended words have any clip. Only 19 meet raw reference-count/speaker/held-out-presence prerequisites. These counts are not clinician approval.
- Owned eval metadata: 11 child recordings from one pseudonymous child, 13 therapist recordings and 2 environment captures. Child rows have no canonical target, age, documented ethics basis, verified guardian consent, or two item-level qualified ratings.
- The user states that they are the therapist and reviewed the recordings. Preserve this as a self-reported review attestation; it does not supply the missing per-record target/outcome labels, an independent second rating, or guardian consent.
- The assistant cannot act as guardian, sign consent, or serve as a qualified independent human rater. No approval flag has been changed to simulate these roles.
- The post-fix metadata-only audit is `D:\VaakMitraData\reports\release-audit-2026-09-12-r3`: its source and owned-label checksums are recorded in `provenance.json`, `child_audio_read=false`, and `clinical_approved=false`. It confirms 0 approved reference words and blocks child validation for all 11 one-child recordings. The audit does not authenticate any future consent document.

## To unblock child-separated validation

Provide locally stored evidence of the actual guardian's consent and applicable ethics approval under the approved protocol. Supply age eligibility, pseudonymous child/household identifiers, and retention/use constraints. Consent records should identify the authorized protocol and recordings without exposing identity in project logs.

For each recording, the two qualified reviewers independently provide: source sample/checksum, assigned canonical word, label (`target`, `other`, `partial`, `capture_invalid`, or `uncertain`), reviewer identity/provenance, and adjudication when they disagree. Document duplicate/near-duplicate and derived-parent groups before splitting.

Separate children into calibration and untouched final evaluation groups. One child cannot be divided by clips to meet this requirement. Additional representative children and negative/confusable examples are required to assess the predeclared false-PASS and subgroup gates; two children alone would not establish statistical or clinical sufficiency.

The metadata audit must pass before authorized local child inference. Passing metadata preflight is not consent authentication, qualified-rater verification, accuracy evidence, or clinical approval by itself.

## To finish adult coverage and release canaries

Use `D:\VaakMitraData\reports\release-audit-2026-09-12-r2\adult-recording-requirements.csv` as the inventory and accepted-reference gap list, not an approval list. Additional accepted references may come from reviewing eligible existing clips; these counts are not automatically a requirement to record every clip again. Each active word requires 32–64 accepted adult references from at least eight speakers, at most four per speaker, plus held-out examples, classifier coverage and review. Do not count repeated clips, synthesis, OTHER labels or invalid audio as accepted target references. The latest source-hash-bound audit reports83words with clips,19raw-count prerequisites, zero qualifying human-approved reference words.

Release canaries need reviewed positive, confusable and invalid-capture cases independent of fitting/reference data, with fixed expected outcomes, checksums, consent/licence basis and reviewer evidence. The current real-model smoke tests are engineering evidence, not approved release canaries. The old adult evaluation partition used for the new fusion rebuild must no longer be described as untouched final-test data.

Additional local inventory check: exact whitespace/punctuation-delimited matching in `openslr65-sentences.jsonl` found sentence occurrences for only three of the17missing segmented-bank words: ஓய்வு11occurrences/10speakers, பிஸ்கட்1/1, போ1/1; the other14had none. These are candidate sentence tokens, not verified word clips, accepted references or canaries. None was added to the83-word segmented inventory or to calibration. New recordings or additional appropriately licensed sources and genuine review are still needed for full coverage.
