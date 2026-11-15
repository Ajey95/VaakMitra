const LABELS = {
  'breath-balloon': 'Breath Balloon',
  'river-rescue': 'River Rescue',
  'mouth-mirror': 'Mouth Mirror',
  pippin: 'Pippin',
  'talk-together': 'Talk Together',
}

function readableId(id) {
  return String(id || '').split('-').filter(Boolean).map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`).join(' ') || null
}

export function formatInteractiveSummary(raw = {}) {
  const sessions = Math.max(0, Number(raw.sessions_this_week) || 0)
  const turns = Math.max(0, Number(raw.communication_turns) || 0)
  const independentPercentage = Math.max(0, Math.min(100, Math.round(Number(raw.independent_percentage) || 0)))
  const activityId = raw.most_practised_activity || null
  const trend = (Array.isArray(raw.assistance_trend) ? raw.assistance_trend : [])
    .map((point) => ({
      date: String(point.date || ''),
      independentPercentage: Math.max(0, Math.min(100, Math.round(Number(point.independent_percentage) || 0))),
      supportTurns: Math.max(0, Number(point.support_turns) || 0),
    }))
    .filter((point) => point.date)
    .sort((a, b) => a.date.localeCompare(b.date))
  return {
    empty: sessions === 0,
    sessions,
    turns,
    independentPercentage,
    mostPractisedLabel: activityId ? LABELS[activityId] || readableId(activityId) : null,
    trend,
    recommendation: raw.recommendation || 'Choose one short activity and celebrate every communication attempt.',
  }
}
