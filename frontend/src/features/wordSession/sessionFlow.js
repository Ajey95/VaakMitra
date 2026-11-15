const isAssigned = (plan) => typeof plan?.plan_id === 'string' && plan.status === 'active' &&
  Array.isArray(plan.word_ids) && plan.word_ids.length > 0 && plan.vocabulary_version && plan.session_limits
const isActive = (snapshot) => snapshot?.status === 'active' && snapshot.session_id &&
  snapshot.word_id && snapshot.target_word && snapshot.exercise_version
const phaseFromStatus = (status) => status === 'active' ? 'active' : status === 'paused' ? 'paused' :
  ['ended', 'complete'].includes(status) ? 'ended' : 'blocked'

// SES-003/005: in-memory only. The UI never owns progress or persists voice-derived data.
export function createSessionFlow(api, onChange = () => {}) {
  let generation = 0
  let loadToken = 0
  let inFlight = null
  const submitted = new WeakSet()
  const flow = {
    state: { phase: 'loading', reason: null, plans: [], snapshot: null, result: null, summary: null },
    update(change) { this.state = { ...this.state, ...change }; onChange(this.state) },
    async load() {
      const currentLoad = ++loadToken
      this.update({ phase: 'loading', reason: null })
      try {
        const [assigned, ready] = await Promise.all([api.assignedPlans(), api.scoringReady()])
        if (currentLoad !== loadToken) return
        const plans = (assigned?.plans || []).filter(isAssigned)
        const snapshot = assigned?.open_session || null
        this.update({ plans, snapshot, result: null,
          phase: !ready ? 'blocked' : snapshot?.status === 'paused' ? 'paused' : isActive(snapshot) ? 'active' : snapshot ? 'blocked' : plans.length ? 'select' : 'blocked',
          reason: !ready ? 'scoring_unavailable' : snapshot && !isActive(snapshot) && snapshot.status !== 'paused' ? 'session_unavailable' : !snapshot && !plans.length ? 'assigned_plan_unavailable' : null })
      } catch (error) {
        if (currentLoad !== loadToken) return
        this.update({ phase: 'blocked', reason: error?.response?.data?.detail || 'assigned_plan_unavailable', plans: [], snapshot: null })
      }
    },
    async start(planId) {
      if (this.state.phase !== 'select' || !this.state.plans.some((plan) => plan.plan_id === planId)) throw new Error('assigned_plan_required')
      const token = generation
      this.update({ phase: 'loading', reason: null })
      try {
        const started = await api.start(planId)
        if (token !== generation) {
          if (started?.session_id) try { await api.stop(started.session_id) } catch { /* best effort */ }
          return
        }
        const snapshot = await api.read(started.session_id)
        if (token !== generation) {
          try { await api.stop(started.session_id) } catch { /* best effort */ }
          return
        }
        this.update({ snapshot, phase: isActive(snapshot) ? 'active' : 'blocked', reason: isActive(snapshot) ? null : 'session_unavailable' })
      } catch (error) {
        if (token !== generation) return
        this.update({ phase: 'blocked', reason: error?.response?.data?.detail || 'session_unavailable' })
      }
    },
    submit(audio) {
      if (!isActive(this.state.snapshot) || !['active', 'processing'].includes(this.state.phase)) return Promise.reject(new Error('session_not_active'))
      if (!audio?.size) return Promise.reject(new Error('empty_audio'))
      if (inFlight) return inFlight.audio === audio ? inFlight.promise : Promise.reject(new Error('attempt_in_progress'))
      if (submitted.has(audio)) return Promise.reject(new Error('capture_already_submitted'))
      const attemptId = crypto.randomUUID()
      submitted.add(audio)
      const snapshot = this.state.snapshot
      const token = generation
      const controller = new AbortController()
      this.update({ phase: 'processing', result: null })
      const promise = (async () => {
        try {
          const result = await api.assess({ audio, sessionId: snapshot.session_id, attemptId,
            wordId: snapshot.word_id, targetWord: snapshot.target_word, exerciseVersion: snapshot.exercise_version,
            signal: controller.signal })
          if (token !== generation) return
          // SES-001/005: the assessment's next_exercise_id cannot advance UI state.
          const refreshed = await api.read(snapshot.session_id)
          if (token !== generation) return
          this.update({ result: refreshed?.word_id === snapshot.word_id ? result : null, snapshot: refreshed,
            phase: isActive(refreshed) ? 'active' : refreshed?.status === 'paused' ? 'paused' : 'ended', reason: null })
          if (refreshed?.status === 'complete' || refreshed?.status === 'ended') {
            try { this.update({ summary: await api.summary(snapshot.session_id) }) } catch { /* no fabricated totals */ }
          }
        } catch (error) {
          if (token !== generation) return
          this.update({ phase: 'blocked', reason: error?.response?.data?.detail || 'assessment_unavailable', result: null })
        } finally {
          if (inFlight?.controller === controller) inFlight = null
        }
      })()
      inFlight = { audio, controller, promise }
      return promise
    },
    async transition(action) {
      const id = this.state.snapshot?.session_id
      if (!id || !['pause', 'stop'].includes(action)) return
      const token = ++generation
      inFlight?.controller.abort()
      inFlight = null
      this.update({ phase: 'blocked', reason: action === 'pause' ? 'pausing' : 'stopping', result: null })
      try {
        const changed = await api[action](id)
        if (token !== generation) return
        const phase = phaseFromStatus(changed?.status)
        this.update({ snapshot: { ...this.state.snapshot, ...changed }, phase,
          reason: phase === 'blocked' ? 'session_unavailable' : null })
        if (phase === 'ended') {
          try {
            const summary = await api.summary(id)
            if (token === generation) this.update({ summary })
          } catch { /* no fabricated totals */ }
        }
      } catch (error) {
        if (token !== generation) return
        this.update({ phase: 'blocked', reason: error?.response?.data?.detail || 'session_unavailable' })
      }
    },
    pause() { return this.transition('pause') },
    stop() { return this.transition('stop') },
    async resume() {
      const snapshot = this.state.snapshot
      if (this.state.phase !== 'paused' || snapshot?.pause_reason !== 'user_pause') throw new Error('voluntary_break_required')
      const token = ++generation
      this.update({ phase: 'blocked', reason: 'resuming', result: null })
      try {
        const resumed = await api.resume(snapshot.session_id)
        if (token !== generation) return
        this.update({ snapshot: resumed, phase: isActive(resumed) ? 'active' : 'blocked',
          reason: isActive(resumed) ? null : 'session_unavailable' })
      } catch (error) {
        if (token !== generation) return
        this.update({ phase: 'paused', reason: error?.response?.data?.detail || 'session_unavailable' })
      }
    },
    async leave() {
      generation += 1
      loadToken += 1
      inFlight?.controller.abort()
      inFlight = null
      const snapshot = this.state.snapshot
      this.state = { ...this.state, result: null, phase: 'ended' }
      if (snapshot?.session_id && ['active', 'paused'].includes(snapshot.status)) {
        try { await api.stop(snapshot.session_id) } catch { /* navigation is best-effort; server expiry remains authoritative */ }
      }
    },
  }
  return flow
}
