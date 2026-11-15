// DEC-008: static operator previews are never scoring evidence or live responses.
const SIMULATIONS = Object.freeze({
  pass: {
    decision: 'PASS', reason_code: 'CALIBRATED_TARGET_MATCH', word_match_probability: 0.94,
    response_intent: 'CELEBRATE', avatar_state: 'CELEBRATE', next_exercise_id: 'TA_WORD_0002',
  },
  retry: {
    decision: 'RETRY', reason_code: 'CALIBRATED_WORD_MISMATCH', word_match_probability: 0.18,
    response_intent: 'ENCOURAGE_RETRY', avatar_state: 'COACH', next_exercise_id: null,
  },
  invalid: {
    decision: 'UNSCORABLE', reason_code: 'INVALID_AUDIO', word_match_probability: null,
    response_intent: 'NEUTRAL_RETRY', avatar_state: 'COACH', next_exercise_id: null,
  },
  capability: {
    decision: 'UNSCORABLE', reason_code: 'MODEL_UNAVAILABLE', word_match_probability: null,
    response_intent: 'CAREGIVER_TECHNICAL_HELP', avatar_state: 'BREAK', next_exercise_id: null,
  },
})

export function simulationFor(key) {
  if (!Object.hasOwn(SIMULATIONS, key)) throw new Error('unknown_simulation')
  return { source: 'simulation', result: { ...SIMULATIONS[key] } }
}
