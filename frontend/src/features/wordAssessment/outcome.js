const CAPABILITY_REASONS = new Set([
  'MODEL_UNAVAILABLE',
  'MODEL_INTEGRITY_MISMATCH',
  'CALIBRATION_UNAVAILABLE',
  'ARTIFACT_MISMATCH',
])

export function wordAssessmentOutcome(result) {
  if (result?.decision === 'PASS') {
    return {
      kind: 'success',
      canCelebrate: true,
      showEvidenceBar: false,
      heading: 'Great! Pippin heard the word clearly.',
      detail: 'Ready for the next word.',
    }
  }
  if (result?.decision === 'RETRY') {
    return {
      kind: 'retry',
      canCelebrate: false,
      showEvidenceBar: false,
      heading: "Good try! Let's say the word once more.",
      detail: 'Take your time and listen to the example again.',
    }
  }

  const capabilityIssue = CAPABILITY_REASONS.has(result?.reason_code)
  return {
    kind: 'unscorable',
    canCelebrate: false,
    showEvidenceBar: false,
    heading: capabilityIssue
      ? 'The word checker is unavailable. Your speech was not graded.'
      : 'Pippin could not check that safely. Your speech was not graded.',
    detail: capabilityIssue
      ? 'A grown-up can check the local model setup.'
      : 'Try again when you are ready, or continue without a score.',
  }
}

