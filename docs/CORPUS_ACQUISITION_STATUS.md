# Tamil corpus acquisition status

Evidence date: 2026-09-07. This file records live acquisition facts for the large-vocabulary plan. It is not child-validation or clinical evidence.

## Storage boundary

- Repository: `D:\VaakMitra-Integrated-Backend` contains code, schemas, source registry, and reports only.
- Raw/build cache: `D:\VaakMitraData` contains downloaded public data and resumable partials.
- Provided `eval/` child recordings remain untracked and excluded from training, reference selection, calibration, and canary approval.
- Free space before the large OpenSLR download attempt: 88.48 GB on `D:`.

## Implemented acquisition controls

- `backend/app/vaakmitra_word/acquisition.py` now requires a source ID, pinned revision, expected byte count, SHA-256, URL, and safe cache-relative path.
- HTTP range resumption writes only to `.part`; promotion to the final filename is atomic and occurs only after size and SHA-256 match.
- Existing verified files are reused without network traffic. Existing conflicting files, disabled sources, unknown licences, and revision drift fail closed.
- Machine-readable reports are stored outside Git in `D:\VaakMitraData\reports\acquisition`.
- The four cached MLCommons artifacts below were independently re-read and recorded as `reused` with exact size and SHA-256 on 2026-09-06.

## MLCommons Multilingual Spoken Words — Tamil

- Hub ID: `MLCommons/ml_spoken_words`
- Pinned revision: `0bc9df68e92fd6bb54176bf7eb29e2b9e97cb218`
- Recorded licence: CC BY 4.0
- Local root: `D:\VaakMitraData\raw\ml_spoken_words`
- Live inventory: 1,884 valid word clips, 190 distinct keywords, 92 pseudonymous speakers.
- Extraction: all 1,884 Opus clips are present under `D:\VaakMitraData\extracted\mswc-ta`.
- Governed manifest: `D:\VaakMitraData\manifests\mswc-ta-other.jsonl`, SHA-256 `80215ab4209410f7de751798cb61e70895ff8fb19600447535c3453a29b5af91`.
- Speaker-disjoint manifest counts: 1,530 train, 152 calibration, 202 evaluation; 1,884 `OTHER`, zero target records.
- Prepared corpus: 1,841 accepted 16 kHz mono WAV clips; 43 rejected (`no_speech`: 42, `excessive_clipping`: 1). The prepared split is 1,493 train, 150 calibration, and 198 evaluation across 92 speakers.
- Prepared manifest SHA-256: `b665337bebda6a7c6048861507c95396a4d2f4f855e798abfa459329a8cda80a`; preprocessing report SHA-256: `590d6c12aa205a7328ccab57d56cd45ad4c684e999d102ed456deee845393c9f`.
- GPU embeddings: all 1,841 accepted samples reconciled across 29 immutable, hash-checked shards; extraction report SHA-256 `2ebda6d6b6b2dd3ee23887ff32975a7e0a4594293e54344aedc0ea5ae329bf1e`.
- Exact overlap with the intended 100-word functional registry: 0 words.
- Decision: retain all 1,884 clips as governed `OTHER`/confusable candidates; do not place them in target reference classes.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Tamil train Opus archive | 8,710,078 | `c5d11d782631f656fba28ba755854ec5e7bfccbd94c46500e3c2ffede2ea984a` |
| Tamil dev Opus archive | 1,919,697 | `4b900e7261dd7c784f4573231a477d8cebd4add3bba95865df927b380bc16a64` |
| Tamil test Opus archive | 1,914,274 | `e75fb823f80e531be3d8e0ea878afcc2a577dd91dc15721b98b88bbbaff91c79` |
| Tamil split metadata | 37,261 | `e654beeeb037413e599ad81b11db244f4734447b43c8f9d4a089ec14bb655402` |

Windows `tar.exe` could not decode Tamil archive filenames. WSL Ubuntu 24.04 GNU tar extracted them successfully. The reproducible manifest builder now resolves the extracted Unicode filenames, hashes every clip, pseudonymizes speakers, and ignores the upstream row split in favor of one deterministic speaker-level split.

## OpenSLR 65 — crowdsourced Tamil multi-speaker speech

- Source: `https://openslr.org/65/`
- Recorded licence: CC BY-SA 4.0
- Official audio is fully downloaded and ZIP-readable: 769,504,014-byte female archive and 603,800,641-byte male archive.
- Archive SHA-256: female `fe00da10ae12ecd6dbe1afcc5abe365d44ad9036fb017cbd73bcfed71e0f8c81`; male `80e546e954939c92a0cd732446418b583b61da9f538f83b00cbd445cbebd4395`.
- Extraction: all 4,291 indexed WAV files are present under `D:\VaakMitraData\extracted\openslr65` (2,335 female and 1,956 male).
- Transcript inventory: 4,291 sentences across 50 pseudonymous speaker prefixes.
- Governed manifest: `D:\VaakMitraData\manifests\openslr65-sentences.jsonl`, SHA-256 `1b79cc05db9d6aff5606a48261e27528ca96a0f44ede9a9abda4df3416ba5ea1`.
- Speaker-disjoint manifest counts: 3,031 train, 581 calibration, 679 evaluation; 4,291 `OTHER`, zero target records. Seven upstream rows with blank transcripts remain traceable as `transcript=null` because their audio is valid and they are not treated as target labels.
- Prepared corpus: 4,264 accepted 16 kHz mono WAV files; 27 rejected for `unsupported_duration`. Prepared splits are 3,014 train, 577 calibration, and 673 evaluation across the same 50 speakers.
- Prepared manifest SHA-256: `e0c93d3b5d8d5d97dcbe75eeb9b64cb4720e0b032074087c135d4c44bff165f8`; preprocessing report SHA-256: `cbf94c955545e1e40fdaa8854f76bdded4081cf508e168d705e3697ccc24c507`.
- Exact overlap: 49 of 100 intended words occur at least once.
- Pre-alignment quota: 4 words have at least 32 sentence occurrences from at least eight speakers.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Female line index | 447,414 | `533be052af53b1c52028a15dd4e41896d274de21bd84bb59e8bf6bbfe535be22` |
| Male line index | 380,966 | `1a0c01afbc8f53538f860903e70461c494bdfb94a0ab8c379324cec0cb4e6a2e` |

Sentence occurrence is only a candidate count. These utterances are intentionally not embedded for the word classifier as whole sentences: a sentence becomes a word reference or word-level negative only after forced segmentation/alignment, exact transcript mapping, quality checks, speaker balancing, deduplication, and human review.

## OpenSLR 127 — IISc-MILE Tamil ASR

- Source: `https://openslr.org/127/`
- Recorded licence: CC BY 2.0
- Official archive: 13,803,410,250 bytes, approximately 150 hours and 531 speakers.
- HTTP ETag: `336bf534a-5e2b7e67be13b`; byte ranges supported.
- Local resumable partial: `D:\VaakMitraData\raw\openslr127\mile_tamil_asr_corpus.tar.gz`, 8,183,808 bytes.
- The fastest official mirror measured approximately 0.32 MB/s, implying roughly 12 hours. The transfer was stopped cleanly; `curl --continue-at -` can resume it.

A Hugging Face conversion mirror (`deepdml/iisc-mile-tamil-asr`, revision `32f434a8e3fe6705304964fffd90dab3383ee6d1`) was used only for remote transcript/index analysis. It is not yet an approved audio origin.

Remote analysis across all 48 train Parquet shards found:

- 91 of the 100 intended words have at least one exact token occurrence;
- 39 words have at least 32 sentence occurrences from at least eight speaker prefixes before segmentation/quality rejection;
- nine absent exact targets: `கழிப்பறை`, `மாம்பழம்`, `சாறு`, `பிஸ்கட்`, `உட்கார்`, `எடு`, `எழுது`, `கைபேசி`, and `மன்னிக்கவும்`.

The 39-word pre-alignment result is not an active bank count. Alignment and quality filtering will reduce it.

## Gated and rejected candidates

- `ai4bharat/Kathbath`, revision `5b9e92849222026d9141acba4e8434fe816396bf`, advertises CC BY 4.0 but the current account does not have dataset approval. It remains disabled in the source registry. Dataset terms must not be accepted automatically on the owner’s behalf.
- `SPRINGLab/IndicVoices-R_Tamil` is accessible and large, but its mirror README declares no licence, while the upstream AI4Bharat corpus is gated. It is blocked by the provenance gate.
- Sources with unknown terms, non-commercial/no-derivatives restrictions, or missing speaker identity cannot become adult reference-bank inputs.

## Next executable work

1. Segment OpenSLR 65 target occurrences, run quality/deduplication, then compute actual per-word/speaker eligibility.
2. Resume OpenSLR 127 only with the governed range downloader and progress ledger, or use a faster verified official mirror if one becomes available.
3. Expand accepted word-level `OTHER`/confusable data from 1,841 to the mandatory minimum of 10,000; do not count unsegmented sentences toward this gate.
4. Activate only words with 32–64 accepted references from at least eight speakers; keep the rest visibly intended/inactive.
