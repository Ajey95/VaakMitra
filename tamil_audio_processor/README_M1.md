# ASD-Edge-ST 2.0 - Member 1 (Audio & Alignment)

This module implements the local audio processing and CTC forced-alignment backend for the ASD-Edge-ST 2.0 system.

## Components
1. **Audio Capture (`src/audio/audio_capture_service.py`)**: Local in-memory audio buffering with no disk I/O, conforming strictly to the "airplane mode" and privacy restrictions.
2. **VAD and Validation (`src/audio/vad_service.py`, `src/audio/audio_quality_validator.py`)**: Extracts speech segments (with high pause tolerance for ASD children) and validates recording quality to prevent negative scoring on bad captures.
3. **Tamil G2P (`src/g2p/tamil_g2p_engine.py`)**: Maps target text to expected phonemes and syllables using a version-controlled JSON dictionary (`pronunciation_dictionary.json`).
4. **CTC Forced Alignment (`src/alignment/forced_aligner.py`)**: Performs Viterbi decoding over Member 2's acoustic probability tensors to yield exact phoneme timestamps and alignment confidence scores.

## Contracts
- `src/alignment/alignment_contract.json`: Defines the JSON response schema for Member 3's orchestration layer.

## Setup and Testing
Ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

Run tests via:
```bash
python -m unittest discover tests
```
