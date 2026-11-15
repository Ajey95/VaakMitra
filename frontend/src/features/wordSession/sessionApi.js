// DEC-003, SES-001: plan and current word are always read from the authenticated server.
export function createSessionApi(client) {
  const sessionPath = (id) => `/api/v1/word-sessions/${encodeURIComponent(id)}`
  return {
    assignedPlans: async () => (await client.get('/api/v1/word-plans/assigned')).data,
    scoringReady: async () => {
      try {
        const response = await client.get('/health/scoring')
        return response.data?.ready === true
      } catch { return false }
    },
    start: async (planId) => (await client.post('/api/v1/word-sessions', { plan_id: planId })).data,
    read: async (id) => (await client.get(sessionPath(id))).data,
    pause: async (id) => (await client.post(`${sessionPath(id)}/pause`)).data,
    resume: async (id) => (await client.post(`${sessionPath(id)}/resume`, {})).data,
    stop: async (id) => (await client.post(`${sessionPath(id)}/stop`)).data,
    summary: async (id) => (await client.get(`${sessionPath(id)}/summary`)).data,
    assess: async ({ audio, sessionId, attemptId, wordId, targetWord, exerciseVersion, signal }) => {
      const form = new FormData()
      form.append('audio', audio, 'attempt.wav')
      form.append('session_id', sessionId)
      form.append('attempt_id', attemptId)
      form.append('word_id', wordId)
      form.append('target_word', targetWord)
      form.append('exercise_version', exerciseVersion)
      return (await client.post('/api/v1/word-assessments', form, { signal })).data
    },
  }
}
