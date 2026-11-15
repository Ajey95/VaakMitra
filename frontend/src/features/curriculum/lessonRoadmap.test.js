import { describe, expect, it } from 'vitest'

import { buildLessonRoadmap, lessonSlideSequence } from './lessonRoadmap'


describe('buildLessonRoadmap', () => {
  it('keeps every server-provided lesson instead of imposing a six-item ceiling', () => {
    const lessons = Array.from({ length: 104 }, (_, index) => ({
      id: index + 1,
      type: index < 4 ? 'letter' : 'word',
      symbol: `தமிழ்-${index + 1}`,
      english: `lesson-${index + 1}`,
      scoreable: index >= 4,
    }))

    const roadmap = buildLessonRoadmap(lessons)

    expect(roadmap).toHaveLength(104)
    expect(roadmap.at(-1).id).toBe(104)
  })

  it('marks teaching-only letters as learnable but not scoreable', () => {
    const [lesson] = buildLessonRoadmap([
      { id: 1, type: 'letter', symbol: 'அ', english: 'A', scoreable: false },
    ])

    expect(lesson.status).toBe('teaching')
    expect(lesson.canOpen).toBe(true)
    expect(lesson.canScore).toBe(false)
  })

  it('keeps intended words visible while their evidence is still unavailable', () => {
    const [lesson] = buildLessonRoadmap([
      {
        id: 5,
        type: 'word',
        symbol: 'அம்மா',
        english: 'mother',
        scoreable: false,
        state: 'intended',
        availability_reason: 'word_not_active_and_approved',
      },
    ])

    expect(lesson.status).toBe('preparing')
    expect(lesson.canOpen).toBe(false)
    expect(lesson.canScore).toBe(false)
    expect(lesson.statusDetail.toLowerCase()).toContain('reference')
  })

  it('rejects malformed API payloads without a static fallback', () => {
    expect(buildLessonRoadmap(undefined)).toEqual([])
    expect(buildLessonRoadmap({ lessons: [] })).toEqual([])
  })

  it('never sends teaching-only letters through the word scoring slide', () => {
    expect(lessonSlideSequence({ type: 'letter', scoreable: false })).toEqual([1, 2, 5])
    expect(lessonSlideSequence({ type: 'word', scoreable: true })).toEqual([1, 2, 3, 4, 5])
  })
})
