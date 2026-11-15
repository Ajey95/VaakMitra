export const ASSISTANCE_LEVELS = ['independent', 'verbal_prompt', 'visual_prompt', 'modelled', 'skipped']

export const TALK_TOGETHER_MISSIONS = Object.freeze([
  { id: 'ask-water', environment: 'kitchen', environmentIndex: 0, title: 'Water Request', childPrompt: 'Show or tell me that you want water.', caregiverCue: 'Pause with a cup in view and wait for any word, sound, picture, or gesture.', celebrate: 'You asked for what you needed!', celebrateTa: 'சிறப்பாக கேட்டாய்!', icon: '💧' },
  { id: 'choose-snack', environment: 'grocery', environmentIndex: 1, title: 'Snack Choice', childPrompt: 'Choose between the two snacks.', caregiverCue: 'Offer two familiar pretend snacks and wait without rushing.', celebrate: 'You made a choice!', celebrateTa: 'அருமையான தேர்வு!', icon: '🍎' },
  { id: 'name-object', environment: 'classroom', environmentIndex: 2, title: 'Find and Name', childPrompt: 'Find one familiar object and show or name it.', caregiverCue: 'Point to two nearby objects and let the child choose one.', celebrate: 'You found it!', celebrateTa: 'நன்றாக கண்டுபிடித்தாய்!', icon: '⭐' },
  { id: 'imitate-turns', environment: 'park', environmentIndex: 3, title: 'Copy My Turn', childPrompt: 'Copy me, then let me copy you.', caregiverCue: 'Model one simple sound, gesture, or word, then swap roles.', celebrate: 'You shared two turns!', celebrateTa: 'மாறி மாறி அருமையாக செய்தாய்!', icon: '👏' },
  { id: 'say-thanks', environment: 'birthday', environmentIndex: 4, title: 'Kind Thank You', childPrompt: 'Say, show, or choose thank you.', caregiverCue: 'Offer a pretend gift and wait for any thank-you response.', celebrate: 'You used a kind message!', celebrateTa: 'மிகவும் அருமை!', icon: '🎁' },
])

export const TALK_TOGETHER_ACTIVITY = Object.freeze({
  id: 'talk-together',
  type: 'talk_together',
  maxAttempts: 1,
  steps: TALK_TOGETHER_MISSIONS.map((mission) => ({ id: mission.id, shortLabel: mission.title, responseMode: 'caregiver_confirm', reward: 2 })),
})

export function summarizeAssistance(events) {
  return Object.fromEntries(ASSISTANCE_LEVELS.map((level) => [level, events.filter((event) => event.assistance === level).length]))
}

export function advanceMission(state) {
  if (state.missionIndex >= TALK_TOGETHER_MISSIONS.length - 1) return { missionIndex: state.missionIndex, complete: true }
  return { missionIndex: state.missionIndex + 1, complete: false }
}

export function buildTalkTogetherReport({ startedAt, completedAt, events = [] }) {
  const start = Number(startedAt) || Date.now()
  const end = Math.max(start, Number(completedAt) || start)
  return {
    activity_id: 'talk-together',
    activity_type: 'talk_together',
    started_at: new Date(start).toISOString(),
    completed_at: new Date(end).toISOString(),
    communication_turns: events.length,
    successful_turns: events.filter((event) => event.assistance !== 'skipped').length,
    attempts: events.length,
    assistance_counts: summarizeAssistance(events),
    duration_ms: Math.min(3_600_000, end - start),
    effort_points: events.filter((event) => event.assistance !== 'skipped').length * 2,
  }
}
