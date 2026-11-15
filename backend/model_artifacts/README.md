# VaakMitra model artifacts

This directory contains documentation only. Production speech artifacts are installed outside Git and validated before use (VM-SSOT-3.0, MOD-003 and FUS-007).

A scoring bundle must contain compatible, cross-hashed versions of the Tamil IndicConformer model, closed-word classifier, approved adult/reference embedding bank, Tamil vocabulary, and therapist-labelled calibration artifact. The calibration artifact must be marked approved and name the hashes of every dependency.

Tests construct synthetic artifacts in memory. Passing core tests proves deterministic pipeline behavior only; it does not prove that a real model is installed, accurate, calibrated for autistic Tamil-speaking children, or ready for clinical use.

