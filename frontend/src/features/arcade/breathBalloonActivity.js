const ASSISTANCE_KEYS = ['independent', 'verbal_prompt', 'visual_prompt', 'modelled', 'skipped']

export const BREATH_BALLOON_ACTIVITY = Object.freeze({
  id: 'breath-balloon',
  type: 'arcade',
  maxAttempts: 3,
  steps: [
    { id: 'gentle-lift', shortLabel: 'Gentle', label: 'Lift gently', responseMode: 'airflow', target: [0.15, 0.45], timeoutMs: 20_000, allowSkip: true, reward: 3 },
    { id: 'steady-float', shortLabel: 'Steady', label: 'Keep it floating', responseMode: 'airflow', target: [0.3, 0.65], timeoutMs: 20_000, allowSkip: true, reward: 3 },
    { id: 'sky-high', shortLabel: 'Sky high', label: 'Send it sky high', responseMode: 'airflow', target: [0.45, 0.78], timeoutMs: 20_000, allowSkip: true, reward: 3 },
  ],
})

export function createBreathBalloonReport({ startedAt, completedAt, scores = [], attempts = 0, assistance = {}, effortPoints = 0 }) {
  const assistanceCounts = Object.fromEntries(ASSISTANCE_KEYS.map((key) => [key, Math.max(0, Number(assistance[key]) || 0)]))
  const start = Number(startedAt) || Date.now()
  const end = Math.max(start, Number(completedAt) || start)
  return {
    activity_id: BREATH_BALLOON_ACTIVITY.id,
    activity_type: BREATH_BALLOON_ACTIVITY.type,
    started_at: new Date(start).toISOString(),
    completed_at: new Date(end).toISOString(),
    communication_turns: scores.length,
    successful_turns: scores.filter((score) => Number(score) > 0).length,
    attempts: Math.max(0, Number(attempts) || 0),
    assistance_counts: assistanceCounts,
    duration_ms: Math.min(3_600_000, end - start),
    effort_points: Math.max(0, Number(effortPoints) || 0),
  }
}
