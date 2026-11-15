export function buildLessonRoadmap(payload) {
  if (!Array.isArray(payload)) return []

  return payload.map((lesson) => {
    const isTeachingLetter = lesson.type === 'letter'
    const canScore = lesson.type === 'word' && lesson.scoreable === true
    const status = isTeachingLetter ? 'teaching' : canScore ? 'available' : 'preparing'
    const statusDetail = isTeachingLetter
      ? 'Teaching activity only; letters are not graded as whole words.'
      : canScore
        ? `Practise and check “${lesson.symbol}”.`
        : 'Reference, classifier and review evidence is still being prepared.'

    return {
      ...lesson,
      letter: lesson.symbol,
      roman: lesson.english,
      status,
      statusDetail,
      canOpen: isTeachingLetter || canScore,
      canScore,
    }
  })
}

export function lessonSlideSequence(lesson) {
  return lesson?.type === 'word' && lesson?.scoreable === true
    ? [1, 2, 3, 4, 5]
    : [1, 2, 5]
}
