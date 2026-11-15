const AGE_COPY = {
  'choose-path': {
    early: { prompt: 'Which way should we go?', hint: 'Tap one path.' },
    middle: { prompt: 'Choose a path to reach Kavi.', hint: 'Both paths are safe.' },
    older: { prompt: 'Choose how our rescue adventure begins.', hint: 'Your choice changes the view.' },
  },
  'call-elephant': {
    early: { prompt: 'Say “aa” to call Kavi!', hint: 'Open wide: aa.' },
    middle: { prompt: 'Call Kavi with a long “aa”.', hint: 'Take a breath, then say aa.' },
    older: { prompt: 'Use one clear, long “aa” to call Kavi.', hint: 'Keep the vowel smooth.' },
  },
  'ask-help': {
    early: { prompt: 'Say “amma, help”.', hint: 'You can say just amma.' },
    middle: { prompt: 'Ask for help: “amma, help”.', hint: 'Try one word at a time.' },
    older: { prompt: 'Use a clear help phrase: “amma, help please”.', hint: 'A short phrase is enough.' },
  },
  'lower-bridge': {
    early: { prompt: 'Blow gently to lower the bridge!', hint: 'A long, soft breath.' },
    middle: { prompt: 'Use a steady breath to lower the bridge.', hint: 'Keep the air moving.' },
    older: { prompt: 'Hold a controlled breath for the bridge rope.', hint: 'Steady is better than strong.' },
  },
  celebrate: {
    early: { prompt: 'Kavi crossed! What will you say?', hint: 'Choose one happy word.' },
    middle: { prompt: 'The rescue worked. Choose a celebration!', hint: 'Tap your favourite.' },
    older: { prompt: 'Finish the quest with a kind or joyful word.', hint: 'Either choice completes the story.' },
  },
}

const ASSISTANCE_KEYS = ['independent', 'verbal_prompt', 'visual_prompt', 'modelled', 'skipped']

export const RIVER_RESCUE_ACTIVITY = Object.freeze({
  id: 'river-rescue',
  type: 'quest',
  maxAttempts: 3,
  steps: [
    { id: 'choose-path', shortLabel: 'Path', responseMode: 'choice', choices: ['forest', 'river'], reward: 2 },
    { id: 'call-elephant', shortLabel: 'Call', responseMode: 'speech', targets: ['aa', 'ஆ'], reward: 3 },
    { id: 'ask-help', shortLabel: 'Ask', responseMode: 'speech', targets: ['amma', 'அம்மா', 'help'], reward: 3 },
    { id: 'lower-bridge', shortLabel: 'Bridge', responseMode: 'airflow', targetDurationMs: 1500, reward: 3 },
    { id: 'celebrate', shortLabel: 'Hooray', responseMode: 'choice', choices: ['nandri', 'hooray'], reward: 2 },
  ],
})

export function getQuestCopy(stepId, ageBand = 'middle') {
  const variants = AGE_COPY[stepId]
  return variants ? variants[ageBand] || variants.middle : null
}

export function resolvePathScene(path) {
  return ['forest', 'river'].includes(path) ? { path, nextStepId: 'call-elephant' } : null
}

function normalizeSpeech(value) {
  return String(value || '').trim().toLocaleLowerCase().replace(/[.,!?]/g, '')
}

export function evaluateQuestResponse(step, response = {}, attempt = 1) {
  let success = false
  if (step?.responseMode === 'choice') success = step.choices.includes(response.choice)
  if (step?.responseMode === 'speech') {
    const heard = normalizeSpeech(response.transcript)
    success = step.targets.some((target) => heard.includes(normalizeSpeech(target)))
  }
  if (step?.responseMode === 'airflow') success = Number(response.durationMs) >= step.targetDurationMs
  const support = !success && attempt >= RIVER_RESCUE_ACTIVITY.maxAttempts
  return { success, support, canAdvance: success || support }
}

export function buildRiverRescueReport({ startedAt, completedAt, turns, successes, attempts, assistance = {}, effortPoints = 0 }) {
  const start = Number(startedAt) || Date.now()
  const end = Math.max(start, Number(completedAt) || start)
  return {
    activity_id: RIVER_RESCUE_ACTIVITY.id,
    activity_type: RIVER_RESCUE_ACTIVITY.type,
    started_at: new Date(start).toISOString(),
    completed_at: new Date(end).toISOString(),
    communication_turns: Math.max(0, Number(turns) || 0),
    successful_turns: Math.max(0, Number(successes) || 0),
    attempts: Math.max(0, Number(attempts) || 0),
    assistance_counts: Object.fromEntries(ASSISTANCE_KEYS.map((key) => [key, Math.max(0, Number(assistance[key]) || 0)])),
    duration_ms: Math.min(3_600_000, end - start),
    effort_points: Math.max(0, Number(effortPoints) || 0),
  }
}
