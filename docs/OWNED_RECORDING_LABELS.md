# Owned evaluation-recording label audit

Evidence date: 2026-09-07. The owner authorized local project use and machine-assisted descriptive labelling in the conversation identified as `owner-message-2026-09-07`. This authorization does not by itself establish clinical consent, therapist ground truth, ethics approval, or permission to publish the recordings.

## Result

- Input: 26 PCM WAV files under the untracked private `eval/` directory.
- Speaker-series labels: 11 child, 13 adult therapist, and 2 environmental recordings.
- Content labels: isolated vocalizations, syllable sequences, prompted sentence sequences, spontaneous speech, one child word sequence, and environmental noise.
- Local IndicConformer transcripts: 22 non-empty and 4 empty.
- Audio gate: 7 satisfy the production utterance envelope; 16 exceed 12 seconds, 2 contain no detected speech, and 1 is below the accepted signal level.
- Eligible adult target-word references: **0**.
- Eligible child training/reference recordings: **0** by policy; child recordings are validation-only.
- Negative-canary candidates: the 2 environmental recordings. They remain candidates until a complete canary suite has active-word positive coverage and reviewer approval.

The private machine-readable inventory is `D:\VaakMitraData\owned\eval-recordings-labels.jsonl`, SHA-256 `fcbd38e4aa46eb830e7a020b5ef958516fc99e64531b23f40c660d994e948e39`. It contains relative filenames, audio hashes, signal measurements, descriptive labels, local model transcripts, and the explicit authorization/consent distinction. It does not copy raw audio.

## Why none entered the reference bank

The therapist recordings are vowels, syllable sequences, sentences, or spontaneous prompts. The reference-bank contract requires a reviewed isolated adult recording whose complete transcript maps unambiguously to one canonical word. A model transcript cannot replace that ground truth. The child word-sequence recording appears to contain target vocabulary, but it has neither trusted word boundaries nor therapist adjudication and therefore remains child-validation evidence only.

The files are preserved unmodified and untracked. No child audio, transcript, or voice-derived representation is committed to Git or permitted to enter classifier training, DTW references, adult calibration, or release canaries.
