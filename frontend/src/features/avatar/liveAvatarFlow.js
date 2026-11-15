const initialState = (turn = 0) => ({
  active: false,
  phase: 'IDLE',
  targetWord: '',
  turn,
})

/** DEC-025/DLA-001..005: ephemeral adult-lab interaction state, never scoring state. */
export function createLiveAvatarFlow() {
  let state = initialState()
  const current = (turn) => state.active && state.turn === turn

  return {
    get state() { return state },
    start(targetWord) {
      state = { active: true, phase: 'PROMPTING', targetWord: String(targetWord || ''), turn: state.turn + 1 }
      return state
    },
    promptComplete(turn) {
      if (current(turn) && ['PROMPTING', 'RETRY'].includes(state.phase)) state = { ...state, phase: 'LISTENING' }
      return state
    },
    captureComplete(turn) {
      if (current(turn) && state.phase === 'LISTENING') state = { ...state, phase: 'PROCESSING' }
      return state
    },
    resolve(turn, decision, coach) {
      if (!current(turn) || state.phase !== 'PROCESSING') return state
      if (decision === 'DEV_MATCH') state = { ...state, active: false, phase: 'PRAISE' }
      else if (decision === 'DEV_UNAVAILABLE') state = { ...state, active: false, phase: 'ERROR' }
      else if (['DEV_TRY_AGAIN', 'DEV_UNCERTAIN'].includes(decision) && coach?.phase === 'break') {
        state = { ...state, active: false, phase: 'BREAK' }
      } else if (['DEV_TRY_AGAIN', 'DEV_UNCERTAIN'].includes(decision)) {
        state = { ...state, phase: 'COACH' }
      } else state = { ...state, active: false, phase: 'ERROR' }
      return state
    },
    coachComplete(turn) {
      if (current(turn) && state.phase === 'COACH') state = { ...state, phase: 'RETRY' }
      return state
    },
    fail(turn) {
      if (current(turn)) state = { ...state, active: false, phase: 'ERROR' }
      return state
    },
    stop() {
      state = initialState(state.turn + 1)
      return state
    },
  }
}
