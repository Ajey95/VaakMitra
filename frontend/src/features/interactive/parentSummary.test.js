import { describe, expect, it } from 'vitest'
import { formatInteractiveSummary } from './parentSummary'

describe('parent interactive-practice summary', () => {
  it('keeps an empty API summary truthful', () => {
    expect(formatInteractiveSummary({ sessions_this_week: 0, communication_turns: 0, independent_percentage: 0, most_practised_activity: null, assistance_trend: [], recommendation: 'Start practising.' })).toEqual({
      empty: true,
      sessions: 0,
      turns: 0,
      independentPercentage: 0,
      mostPractisedLabel: null,
      trend: [],
      recommendation: 'Start practising.',
    })
  })

  it('formats percentages, labels, trend order, and recommendation', () => {
    const result = formatInteractiveSummary({
      sessions_this_week: 3,
      communication_turns: 12,
      independent_percentage: 67.6,
      most_practised_activity: 'river-rescue',
      assistance_trend: [
        { date: '2026-08-01', independent_percentage: 80, support_turns: 1 },
        { date: '2026-07-30', independent_percentage: 40, support_turns: 3 },
      ],
      recommendation: 'Wait quietly after one visual cue.',
    })
    expect(result).toMatchObject({ empty: false, sessions: 3, turns: 12, independentPercentage: 68, mostPractisedLabel: 'River Rescue', recommendation: 'Wait quietly after one visual cue.' })
    expect(result.trend.map((point) => point.date)).toEqual(['2026-07-30', '2026-08-01'])
  })

  it('uses a readable fallback label for a future activity id', () => {
    expect(formatInteractiveSummary({ sessions_this_week: 1, most_practised_activity: 'sound-garden' }).mostPractisedLabel).toBe('Sound Garden')
  })
})
