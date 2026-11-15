# Public adult test fixtures

`backbone-fixtures` and `backbone-capture-fixtures` contain small engineering-test excerpts/variants derived from the MLCommons Multilingual Spoken Words Corpus (MSWC), authored by the corpus contributors. The corpus is licensed under [Creative Commons Attribution4.0](https://creativecommons.org/licenses/by/4.0/); see the [MLCommons dataset source](https://mlcommons.org/datasets/multilingual-spoken-words/) and the original corpus attribution/publication.

The adjacent manifests retain source-row/split identities, original audio hashes, output hashes and preprocessing/variant descriptions. Changes include WAV conversion/resampling, fixed-length/capture-envelope preparation, trimming, silence/quiet boundaries and declared tempo/noise/echo variants. Synthetic transformations are not genuine pronunciation errors. Predicted token sequences are frozen model outputs, not independent phonetic annotations. No expert approval or clinical correctness is implied.

`phoneme-fixtures` carries its own `ATTRIBUTION.txt`; preserve that source-specific attribution with its audio and variants.

No owner-provided child recordings, private adult recordings or live microphone recordings are included. These fixtures do not establish child recognition accuracy or therapy effectiveness. Model licenses and permissions are independent of these dataset licenses; model binaries are not distributed in this source publication.
