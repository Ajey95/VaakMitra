const idle = () => ({ phase: 'idle', cycles: 0, targetWord: '', chunks: [], focusIndex: null,
  basis: 'manual_visual_practice', status: 'visual_only' })

function validHint(hint) {
  return typeof hint?.target_word === 'string' && hint.target_word.length > 0 &&
    Array.isArray(hint.chunks) && hint.chunks.length >= 1 && hint.chunks.length <= 3 &&
    hint.chunks.every((chunk) => typeof chunk === 'string' && chunk.length > 0) &&
    hint.chunks.join('') === hint.target_word &&
    ['visual_only', 'text_hypothesis'].includes(hint.status)
}

/** DEC-023/DCH-003: ephemeral adult rehearsal; no assessment or progress state. */
export function createChunkCoachFlow() {
  let state = idle()
  return {
    get state() { return state },
    reset() { state = idle(); return state },
    start(hint, developmentDecision) {
      if (!['DEV_TRY_AGAIN', 'DEV_UNCERTAIN'].includes(developmentDecision)) {
        state = idle()
        return state
      }
      if (!validHint(hint)) { state = idle(); return state }
      if (state.phase === 'break') return state
      const cycles = state.phase === 'whole_again' && state.targetWord === hint.target_word ? state.cycles + 1 : 0
      state = { phase: cycles >= 2 ? 'break' : 'focus', cycles,
        targetWord: hint.target_word, chunks: [...hint.chunks],
        focusIndex: Number.isInteger(hint.focus_index) && hint.focus_index >= 0 && hint.focus_index < hint.chunks.length
          ? hint.focus_index : 0,
        basis: hint.status === 'text_hypothesis' ? 'unvalidated_asr_text_difference' : 'manual_visual_practice',
        status: hint.status }
      return state
    },
    select(index) {
      if (state.phase === 'focus' && Number.isInteger(index) && index >= 0 && index < state.chunks.length)
        state = { ...state, focusIndex: index, basis: 'manual_visual_practice', status: 'visual_only' }
      return state
    },
    advance() {
      if (state.phase === 'focus') state = { ...state, phase: 'blend' }
      else if (state.phase === 'blend') state = { ...state, phase: 'whole_again' }
      return state
    },
  }
}
