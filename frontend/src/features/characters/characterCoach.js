export const PIPPIN_COACH_MISSIONS = Object.freeze([
  Object.freeze({
    id: 'hello',
    prompt: 'Wave to me and say hello!',
    shorterPrompt: 'Say hello.',
    accepted: Object.freeze(['hello', 'hi', 'vanakkam']),
    choices: Object.freeze([
      Object.freeze({ value: 'hello', label: 'Hello', icon: '👋' }),
      Object.freeze({ value: 'vanakkam', label: 'Vanakkam', icon: '🙏' }),
    ]),
    success: 'Hello, friend! I am so happy to meet you!',
  }),
  Object.freeze({
    id: 'play',
    prompt: 'What should we play with: a ball or a drum?',
    shorterPrompt: 'Choose ball or drum.',
    accepted: Object.freeze(['ball', 'drum']),
    choices: Object.freeze([
      Object.freeze({ value: 'ball', label: 'Ball', icon: '🔵' }),
      Object.freeze({ value: 'drum', label: 'Drum', icon: '🥁' }),
    ]),
    success: 'Great choice! Let us play together!',
  }),
  Object.freeze({
    id: 'move',
    prompt: 'Can you choose an action for me: jump or dance?',
    shorterPrompt: 'Choose jump or dance.',
    accepted: Object.freeze(['jump', 'dance']),
    choices: Object.freeze([
      Object.freeze({ value: 'jump', label: 'Jump', icon: '⬆️' }),
      Object.freeze({ value: 'dance', label: 'Dance', icon: '🎵' }),
    ]),
    success: 'Whee! You gave me a fun action!',
  }),
  Object.freeze({
    id: 'family',
    prompt: 'Choose a family word to practise: Amma or Appa.',
    shorterPrompt: 'Choose Amma or Appa.',
    accepted: Object.freeze(['amma', 'appa']),
    choices: Object.freeze([
      Object.freeze({ value: 'amma', label: 'Amma', icon: '💛' }),
      Object.freeze({ value: 'appa', label: 'Appa', icon: '💙' }),
    ]),
    success: 'Lovely family word. I heard you!',
  }),
  Object.freeze({
    id: 'sound',
    prompt: 'One last sound game! Choose A or La and say it with me.',
    shorterPrompt: 'Choose A or La.',
    accepted: Object.freeze(['a', 'aa', 'la']),
    choices: Object.freeze([
      Object.freeze({ value: 'a', label: 'A', icon: 'அ' }),
      Object.freeze({ value: 'la', label: 'La', icon: 'ல' }),
    ]),
    success: 'You did it! Every sound was a brave try!',
  }),
])

function normalize(value) {
  return String(value ?? '').toLocaleLowerCase('en-IN').replace(/[^a-z\u0B80-\u0BFF ]/g, ' ').replace(/\s+/g, ' ').trim()
}

export function createCoachState() {
  return {
    phase: 'intro',
    missionIndex: 0,
    attempts: 0,
    completedTurns: 0,
    lastAssistance: null,
    lastValue: '',
    message: 'Pippin is ready for a friendly mission!',
  }
}

export function getCoachMission(stateOrIndex = 0) {
  const rawIndex = typeof stateOrIndex === 'number' ? stateOrIndex : stateOrIndex?.missionIndex
  const index = Math.min(PIPPIN_COACH_MISSIONS.length - 1, Math.max(0, Number(rawIndex) || 0))
  return PIPPIN_COACH_MISSIONS[index]
}

function matchesMission(mission, value, intent) {
  const candidates = [normalize(value), normalize(intent)].filter(Boolean)
  return mission.accepted.some((answer) => candidates.some((candidate) => (
    candidate === answer || candidate.split(' ').includes(answer)
  )))
}

export function characterCoachReducer(state, event) {
  switch (event.type) {
    case 'RESET':
      return createCoachState()
    case 'START':
      return { ...createCoachState(), phase: 'prompt', message: getCoachMission(0).prompt }
    case 'PROMPT_STARTED':
      return { ...state, phase: 'speaking', message: getCoachMission(state).prompt }
    case 'PROMPT_FINISHED':
      return { ...state, phase: 'prompt', message: getCoachMission(state).prompt }
    case 'BEGIN_LISTENING':
      return { ...state, phase: 'listening', message: 'Pippin is listening. Take your time!' }
    case 'ANSWER': { // Values are matched only against the current finite mission allow-list.
      const mission = getCoachMission(state)
      const attempts = state.attempts + 1
      if (matchesMission(mission, event.value, event.intent)) {
        return {
          ...state,
          phase: 'success',
          attempts,
          completedTurns: state.completedTurns + 1,
          lastAssistance: event.source === 'voice' ? 'independent' : 'visual_prompt',
          lastValue: normalize(event.value || event.intent),
          message: mission.success,
        }
      }
      const needsSupport = attempts >= 2
      return {
        ...state,
        phase: needsSupport ? 'support' : 'encourage',
        attempts,
        lastValue: normalize(event.value),
        message: needsSupport
          ? `${mission.shorterPrompt} You can tap a picture, too.`
          : `Nice try! ${mission.shorterPrompt}`,
      }
    }
    case 'SKIP':
      return {
        ...state,
        phase: 'success',
        completedTurns: state.completedTurns + 1,
        lastAssistance: 'skipped',
        message: 'That is okay. We can choose the next adventure together!',
      }
    case 'NEXT':
      if (state.phase !== 'success') return state
      if (state.missionIndex >= PIPPIN_COACH_MISSIONS.length - 1) {
        return { ...state, phase: 'complete', message: 'Mission complete! We made a wonderful team!' }
      }
      return {
        ...state,
        phase: 'prompt',
        missionIndex: state.missionIndex + 1,
        attempts: 0,
        lastAssistance: null,
        lastValue: '',
        message: getCoachMission(state.missionIndex + 1).prompt,
      }
    default:
      return state
  }
}
