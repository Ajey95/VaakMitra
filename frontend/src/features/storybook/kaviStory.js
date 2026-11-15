export const KAVI_STORY_PAGES = Object.freeze([
  {
    id: 'a',
    target: 'அ',
    narration: 'கவி ஆற்றங்கரையில் நிற்கிறான். பாதையைத் திறக்க “அ” என்று சொல்லலாமா?',
    scene: 'flowers',
    picture: '/assets/storybook/kavi/level-1.png',
    pictureAlt: 'குட்டி யானை கவி பூக்கள் அருகே நின்று பாலத்தைப் பார்க்கிறான்',
    lineId: 'page_1',
    help: 'வாயை நன்றாகத் திறந்து, கவியுடன் “அ” என்று சொல்லுங்கள்.',
  },
  {
    id: 'ii',
    target: 'ஈ',
    narration: 'மின்மினிப் பூச்சிகள் வழி காட்ட வேண்டும். “ஈ” என்று நீளமாகச் சொல்லுங்கள்.',
    scene: 'fireflies',
    picture: '/assets/storybook/kavi/level-2.png',
    pictureAlt: 'மின்மினிப் பூச்சிகள் கவிக்கு பாலத்தை நோக்கி வழி காட்டுகின்றன',
    lineId: 'page_2',
    help: 'சிரித்த முகத்துடன் “ஈ” என்று கொஞ்சம் நீளமாகச் சொல்லுங்கள்.',
  },
  {
    id: 'amma',
    target: 'அம்மா',
    narration: 'கவி தன் அம்மாவை அழைக்க வேண்டும். “அம்மா” என்று சொல்லுங்கள்.',
    scene: 'family',
    picture: '/assets/storybook/kavi/level-3.png',
    pictureAlt: 'கவி தன் அம்மா யானையை ஆற்றங்கரையில் அன்புடன் சந்திக்கிறான்',
    lineId: 'page_3',
    help: 'அம் — மா. இரண்டு பகுதியாகக் கவியுடன் சொல்லலாம்.',
  },
  {
    id: 'kavi_vaa',
    target: 'கவி வா',
    narration: 'பாலம் அருகே வந்துவிட்டது. “கவி வா” என்று அழையுங்கள்.',
    scene: 'bridge',
    picture: '/assets/storybook/kavi/level-4.png',
    pictureAlt: 'கவி பாதுகாப்பான மரப்பாலத்தின் மீது நடக்கத் தயாராக நிற்கிறான்',
    lineId: 'page_4',
    help: 'முதலில் “கவி”, பிறகு “வா” என்று மெதுவாகச் சொல்லுங்கள்.',
  },
  {
    id: 'kavi_bridge',
    target: 'கவி பாலத்தைக் கடக்கலாம்',
    narration: 'கவி பாலத்தைக் கடக்கத் தயாராக இருக்கிறான். “கவி பாலத்தைக் கடக்கலாம்” என்று சொல்லுங்கள்.',
    scene: 'crossing',
    picture: '/assets/storybook/kavi/level-5.png',
    pictureAlt: 'கவி மகிழ்ச்சியாக பாதுகாப்பான மரப்பாலத்தைக் கடக்கிறான்',
    lineId: 'page_5',
    help: 'படத்தில் உள்ள சொற்களை ஒவ்வொன்றாகக் காட்டி, ஒன்றாகச் சொல்லலாம்.',
  },
])

export function createKaviStoryState(startedAt = 0) {
  return {
    phase: 'intro',
    pageIndex: 0,
    pageAttempts: 0,
    totalAttempts: 0,
    successes: 0,
    assistanceCount: 0,
    feedbackKey: null,
    lastAccuracy: null,
    startedAt,
  }
}

export function getKaviPage(state) {
  return KAVI_STORY_PAGES[Math.min(KAVI_STORY_PAGES.length - 1, Math.max(0, state.pageIndex))]
}

export function kaviStoryReducer(state, event) {
  switch (event.type) {
    case 'START':
    case 'NARRATION_STARTED':
      return {
        ...state,
        phase: 'narrating',
        startedAt: state.startedAt || event.startedAt || Date.now(),
        feedbackKey: null,
      }
    case 'NARRATION_ENDED':
      return state.phase === 'narrating' ? { ...state, phase: 'ready' } : state
    case 'LISTEN':
      return ['ready', 'support'].includes(state.phase)
        ? { ...state, phase: 'listening', feedbackKey: null }
        : state
    case 'EVALUATE':
      return state.phase === 'listening' ? { ...state, phase: 'evaluating' } : state
    case 'RESULT': {
      if (state.phase !== 'evaluating') return state
      const result = event.result || {}
      if (result.capability && result.capability !== 'available') {
        return {
          ...state,
          phase: 'support',
          feedbackKey: result.feedback_key || 'model_unavailable',
          lastAccuracy: null,
        }
      }
      const pageAttempts = state.pageAttempts + 1
      const common = {
        ...state,
        pageAttempts,
        totalAttempts: state.totalAttempts + 1,
        feedbackKey: result.feedback_key || (result.matched ? 'wonderful' : 'try_together'),
        lastAccuracy: Number.isFinite(result.accuracy) ? result.accuracy : null,
      }
      if (result.matched) {
        return { ...common, phase: 'success', successes: state.successes + 1 }
      }
      return { ...common, phase: pageAttempts >= 3 ? 'support' : 'ready' }
    }
    case 'USE_HELP':
      return state.phase === 'support'
        ? {
            ...state,
            phase: 'success',
            assistanceCount: state.assistanceCount + 1,
            successes: state.successes + 1,
            feedbackKey: 'try_together',
          }
        : state
    case 'NEXT':
      return state.phase === 'success' ? { ...state, phase: 'walking' } : state
    case 'WALK_FINISHED':
      if (state.phase !== 'walking') return state
      if (state.pageIndex === KAVI_STORY_PAGES.length - 1) {
        return { ...state, phase: 'complete', feedbackKey: 'complete' }
      }
      return {
        ...state,
        phase: 'narrating',
        pageIndex: state.pageIndex + 1,
        pageAttempts: 0,
        feedbackKey: null,
        lastAccuracy: null,
      }
    case 'RESET':
      return createKaviStoryState()
    default:
      return state
  }
}

export function buildKaviStoryReport({ state, completedAt = Date.now() }) {
  const isComplete = state.phase === 'complete'
  const startedAt = Number.isFinite(state.startedAt) ? state.startedAt : completedAt
  const finishedAt = Math.max(startedAt, completedAt)
  const communicationTurns = isComplete ? KAVI_STORY_PAGES.length : Math.max(0, state.pageIndex)
  const successfulTurns = Math.min(communicationTurns, Math.max(0, state.successes))
  const modelled = Math.min(successfulTurns, Math.max(0, state.assistanceCount))
  return {
    activity_id: 'kavi-tamil-story',
    activity_type: 'quest',
    started_at: new Date(startedAt).toISOString(),
    completed_at: new Date(finishedAt).toISOString(),
    communication_turns: communicationTurns,
    successful_turns: successfulTurns,
    attempts: Math.min(300, Math.max(0, state.totalAttempts)),
    assistance_counts: {
      independent: successfulTurns - modelled,
      verbal_prompt: 0,
      visual_prompt: 0,
      modelled,
      skipped: 0,
    },
    duration_ms: Math.min(3_600_000, finishedAt - startedAt),
    effort_points: successfulTurns * 2,
  }
}
