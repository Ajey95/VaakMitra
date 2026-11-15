import { expect, test } from '@playwright/test'

test.use({
  channel: 'msedge',
  launchOptions: { args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] },
  permissions: ['microphone'],
})

const evidenceDir = 'C:/Users/AJEYA/.codex/visualizations/2026/09/11/01a09207-2ae3-7ba1-a2e7-758f8ac4acb9'
const plan = { plan_id: '0000000000000000000000e1', status: 'active', word_ids: ['TA_WORD_0001'], vocabulary_version: 'ta-words-v1.0.0', session_limits: { max_retries: 2, max_total_attempts: 40, max_session_seconds: 600, break_seconds: 30 } }
const active = { session_id: 'SES-SYNTHETIC', status: 'active', word_id: 'TA_WORD_0001', target_word: 'அம்மா', exercise_version: 'ta-words-v1.0.0', attempt_count: 0, total_attempts: 0 }

test('ux003 ses007 red Break / Stop silences capture before offering End', async ({ page }) => {
  let paused = false
  let ended = false
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/therapy/lessons/5', (route) => route.fulfill({ json: { id: 5, type: 'word', scoreable: true, symbol: 'அம்மா' } }))
  await page.route('**/health/scoring', (route) => route.fulfill({ json: { ready: true } }))
  await page.route('**/api/v1/word-plans/assigned', (route) => route.fulfill({ json: { plans: [plan], open_session: active } }))
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/pause', (route) => {
    paused = true
    return route.fulfill({ json: { ...active, status: 'paused', pause_reason: 'user_pause' } })
  })
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/stop', (route) => {
    ended = true
    return route.fulfill({ json: { session_id: active.session_id, status: 'ended' } })
  })
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/summary', (route) => route.fulfill({ json: { decisions: { PASS: 0, RETRY: 0, UNSCORABLE: 0 } } }))
  await page.goto('/therapy/5')
  await page.getByRole('button', { name: 'Start recording' }).click()
  await expect(page.getByText('Listening now')).toBeVisible()
  await expect(page.getByLabel('Interactive avatar coach')).toHaveAttribute('data-avatar-phase', 'LISTENING')
  await page.getByRole('button', { name: 'Break or stop' }).click()
  await expect(page.getByText('Listening now')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Start recording' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Take a break' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Take a break' })).toBeFocused()
  expect(paused).toBe(true)
  await page.getByRole('button', { name: 'End session' }).click()
  await expect(page.getByRole('heading', { name: 'Session ended' }).first()).toBeVisible()
  expect(ended).toBe(true)
})

test('ses007 Stop remains available after a failed pause request', async ({ page }) => {
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/therapy/lessons/5', (route) => route.fulfill({ json: { id: 5, type: 'word', scoreable: true, symbol: 'அம்மா' } }))
  await page.route('**/health/scoring', (route) => route.fulfill({ json: { ready: true } }))
  await page.route('**/api/v1/word-plans/assigned', (route) => route.fulfill({ json: { plans: [plan], open_session: active } }))
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/pause', (route) => route.fulfill({ status: 503, json: { detail: 'session_unavailable' } }))
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/stop', (route) => route.fulfill({ json: { session_id: active.session_id, status: 'ended' } }))
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/summary', (route) => route.fulfill({ json: { decisions: { PASS: 0, RETRY: 0, UNSCORABLE: 0 } } }))
  await page.goto('/therapy/5')
  await page.getByRole('button', { name: 'Break or stop' }).click()
  await page.getByRole('button', { name: 'Take a break' }).click()
  await expect(page.getByRole('button', { name: 'End session' })).toBeVisible()
  await page.getByRole('button', { name: 'End session' }).click()
  await expect(page.getByRole('heading', { name: 'Session ended' }).first()).toBeVisible()
})

test('ses001/003 synthetic assigned-plan flow shows neutral unavailable result and child stop', async ({ page }) => {
  const errors = []
  const calls = []
  let snapshot = active
  page.on('pageerror', (error) => errors.push(error.message))
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/therapy/lessons/5', (route) => route.fulfill({ json: { id: 5, type: 'word', scoreable: true, symbol: 'அம்மா' } }))
  await page.route('**/health/scoring', (route) => route.fulfill({ json: { ready: true, reasons: [] } }))
  await page.route('**/api/v1/word-plans/assigned', (route) => route.fulfill({ json: { plans: [plan], open_session: null } }))
  await page.route('**/api/v1/word-sessions', (route) => {
    calls.push(['start', route.request().postDataJSON()])
    return route.fulfill({ status: 201, json: active })
  })
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC', (route) => route.fulfill({ json: snapshot }))
  await page.route('**/api/v1/word-assessments', (route) => {
    const body = route.request().postDataBuffer().toString('utf8')
    calls.push(['assess', body])
    snapshot = { ...active, status: 'paused', attempt_count: 0, total_attempts: 1, pause_reason: 'capability' }
    return route.fulfill({ json: { decision: 'UNSCORABLE', reason_code: 'CALIBRATION_UNAVAILABLE', word_match_probability: null, response_intent: 'CAREGIVER_TECHNICAL_HELP' } })
  })
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/stop', (route) => route.fulfill({ json: { session_id: active.session_id, status: 'ended' } }))
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/summary', (route) => route.fulfill({ json: { session_id: active.session_id, status: 'ended', decisions: { PASS: 0, RETRY: 0, UNSCORABLE: 1 } } }))

  await page.goto('/therapy/5')
  await expect(page.getByRole('heading', { name: 'Choose your assigned word plan' })).toBeVisible()
  await expect(page.getByText('1 assigned word · Start practice')).toBeVisible()
  await expect(page.getByText(/approved words/)).toHaveCount(0)
  expect(await page.title()).toMatch(/VaakMitra|SpeakEasy/i)
  await page.getByRole('button', { name: /Assigned word plan 1/ }).click()
  await expect(page.getByRole('button', { name: 'Break or stop' })).toBeVisible()
  await expect(page.getByText('அம்மா').first()).toBeVisible()
  await page.screenshot({ path: `${evidenceDir}/synthetic-session-desktop.png` })

  await page.getByRole('button', { name: 'Start recording' }).click()
  await expect(page.getByText('Listening now')).toBeVisible()
  await page.waitForTimeout(700)
  await page.getByRole('button', { name: 'Stop recording' }).click()
  await expect(page.getByRole('button', { name: 'Check word' })).toBeVisible()
  await page.getByRole('button', { name: 'Check word' }).click()
  await expect(page.getByText('The word checker is unavailable. Your speech was not graded.')).toBeVisible()
  await expect(page.getByText('A grown-up can help continue.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start recording' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Resume session' })).toHaveCount(0)
  expect(calls[0]).toEqual(['start', { plan_id: plan.plan_id }])
  expect(calls[1][1]).toContain('name="target_word"')
  expect(calls[1][1]).toContain('அம்மா')
  expect(calls[1][1]).toContain('ta-words-v1.0.0')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: `${evidenceDir}/synthetic-session-mobile-paused.png`, fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  expect((await page.locator('.training-pippin__message').boundingBox()).width).toBeGreaterThan(200)
  await page.getByRole('button', { name: 'End session' }).click()
  await expect(page.getByRole('heading', { name: 'Session ended' }).first()).toBeVisible()
  await expect(page.getByText('Sharing with a therapist requires separate permission.', { exact: false })).toBeVisible()
  expect(errors).toEqual([])
})

test('ses001 synthetic missing-plan response blocks microphone and session creation', async ({ page }) => {
  let starts = 0
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/therapy/lessons/5', (route) => route.fulfill({ json: { id: 5, type: 'word', scoreable: true, symbol: 'அம்மா' } }))
  await page.route('**/health/scoring', (route) => route.fulfill({ json: { ready: true } }))
  await page.route('**/api/v1/word-plans/assigned', (route) => route.fulfill({ json: { plans: [], open_session: null } }))
  await page.route('**/api/v1/word-sessions', (route) => { starts++; return route.fulfill({ status: 500 }) })
  await page.goto('/therapy/5')
  await expect(page.getByText('There is no current therapist-assigned word plan for this session.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start recording' })).toHaveCount(0)
  expect(starts).toBe(0)
})

test('ses003 synthetic pause cancels microphone permission resolving late', async ({ page }) => {
  await page.addInitScript(() => {
    const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices)
    navigator.mediaDevices.getUserMedia = () => new Promise((resolve) => {
      window.releaseSyntheticMicrophone = async () => {
        const stream = await original({ audio: true })
        window.syntheticMicrophoneStream = stream
        resolve(stream)
      }
    })
  })
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/therapy/lessons/5', (route) => route.fulfill({ json: { id: 5, type: 'word', scoreable: true, symbol: 'அம்மா' } }))
  await page.route('**/health/scoring', (route) => route.fulfill({ json: { ready: true } }))
  await page.route('**/api/v1/word-plans/assigned', (route) => route.fulfill({ json: { plans: [plan], open_session: active } }))
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/pause', (route) => route.fulfill({ json: { ...active, status: 'paused' } }))
  await page.goto('/therapy/5')
  await page.getByRole('button', { name: 'Start recording' }).click()
  await page.getByRole('button', { name: 'Break or stop' }).click()
  await page.evaluate(() => window.releaseSyntheticMicrophone())
  await expect(page.getByText('Practice paused')).toBeVisible()
  await expect.poll(() => page.evaluate(() => window.syntheticMicrophoneStream.getAudioTracks()[0].readyState)).toBe('ended')
  await expect(page.getByRole('button', { name: 'Start recording' })).toHaveCount(0)
})

test('ses003 synthetic route exit stops the known session during a pending assessment', async ({ page }) => {
  let stopCalls = 0
  let releaseAssessment
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/therapy/lessons/5', (route) => route.fulfill({ json: { id: 5, type: 'word', scoreable: true, symbol: 'அம்மா' } }))
  await page.route('**/health/scoring', (route) => route.fulfill({ json: { ready: true } }))
  await page.route('**/api/v1/word-plans/assigned', (route) => route.fulfill({ json: { plans: [plan], open_session: active } }))
  await page.route('**/api/v1/word-assessments', async (route) => {
    await new Promise((resolve) => { releaseAssessment = resolve })
    try { await route.fulfill({ json: { decision: 'PASS', reason_code: 'CALIBRATED_TARGET_MATCH' } }) } catch { /* aborted request */ }
  })
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/stop', (route) => { stopCalls++; return route.fulfill({ json: { session_id: active.session_id, status: 'ended' } }) })
  await page.goto('/therapy/5')
  await expect(page.getByRole('button', { name: 'Start recording' })).toBeVisible()
  await page.getByRole('button', { name: 'Start recording' }).click()
  await page.waitForTimeout(700)
  await page.getByRole('button', { name: 'Stop recording' }).click()
  await page.getByRole('button', { name: 'Check word' }).click()
  await expect.poll(() => typeof releaseAssessment).toBe('function')
  await page.evaluate(() => {
    window.history.pushState({}, '', '/not-a-therapy-route')
    window.dispatchEvent(new PopStateEvent('popstate'))
  })
  await expect.poll(() => stopCalls).toBe(1)
  releaseAssessment()
  await expect(page).not.toHaveURL(/\/therapy\//)
  await expect(page.getByText('Great! Pippin heard the word clearly.')).toHaveCount(0)
})

test('dec016 inherited letter lesson remains visual and silent without session scoring', async ({ page }) => {
  let scoringCalls = 0
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/therapy/lessons/1', (route) => route.fulfill({ json: { id: 1, type: 'letter', scoreable: false, symbol: 'அ', english: 'A', phoneme: 'a', difficulty: 1, tip: 'Look at the shape.' } }))
  await page.route('**/api/v1/word-**', (route) => { scoringCalls++; return route.fulfill({ status: 500 }) })
  await page.goto('/therapy/1')
  await expect(page.getByTestId('lesson-built-in-visual')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Listen' })).toHaveCount(0)
  await page.getByRole('button', { name: /Next/ }).click()
  await expect(page.getByRole('heading', { name: 'Visual practice' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Finish' })).toBeVisible()
  await expect(page.getByRole('button', { name: /Play Audio|Play Video|Evaluate/ })).toHaveCount(0)
  await page.screenshot({ path: `${evidenceDir}/synthetic-letter-visual-desktop.png` })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: `${evidenceDir}/synthetic-letter-visual-mobile.png`, fullPage: true })
  expect(scoringCalls).toBe(0)
})

test('ses003 synthetic Pause stays available while assessment is processing', async ({ page }) => {
  let releaseAssessment
  let pauses = 0
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/therapy/lessons/5', (route) => route.fulfill({ json: { id: 5, type: 'word', scoreable: true, symbol: 'அம்மா' } }))
  await page.route('**/health/scoring', (route) => route.fulfill({ json: { ready: true } }))
  await page.route('**/api/v1/word-plans/assigned', (route) => route.fulfill({ json: { plans: [plan], open_session: active } }))
  await page.route('**/api/v1/word-assessments', async (route) => {
    await new Promise((resolve) => { releaseAssessment = resolve })
    try { await route.fulfill({ json: { decision: 'PASS', reason_code: 'CALIBRATED_TARGET_MATCH' } }) } catch { /* aborted request */ }
  })
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/pause', (route) => {
    pauses++
    return route.fulfill({ json: { ...active, status: 'paused', pause_reason: 'user_pause' } })
  })
  await page.goto('/therapy/5')
  await page.getByRole('button', { name: 'Start recording' }).click()
  await page.waitForTimeout(700)
  await page.getByRole('button', { name: 'Stop recording' }).click()
  await page.getByRole('button', { name: 'Check word' }).click()
  await expect.poll(() => typeof releaseAssessment).toBe('function')
  await expect(page.getByRole('button', { name: 'Break or stop' })).toBeVisible()
  await page.getByRole('button', { name: 'Break or stop' }).click()
  await expect(page.getByText('Practice paused')).toBeVisible()
  releaseAssessment()
  await expect(page.getByText('Great! Pippin heard the word clearly.')).toHaveCount(0)
  expect(pauses).toBe(1)
})

test('ses003 synthetic Stop wins over a late Pause response in the rendered session', async ({ page }) => {
  let releasePause
  let pauseSettled = false
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/therapy/lessons/5', (route) => route.fulfill({ json: { id: 5, type: 'word', scoreable: true, symbol: 'அம்மா' } }))
  await page.route('**/health/scoring', (route) => route.fulfill({ json: { ready: true } }))
  await page.route('**/api/v1/word-plans/assigned', (route) => route.fulfill({ json: { plans: [plan], open_session: active } }))
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/pause', async (route) => {
    await new Promise((resolve) => { releasePause = resolve })
    try { await route.fulfill({ json: { ...active, status: 'paused' } }) } catch { /* late response */ }
    pauseSettled = true
  })
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/stop', (route) => route.fulfill({ json: { session_id: active.session_id, status: 'ended' } }))
  await page.route('**/api/v1/word-sessions/SES-SYNTHETIC/summary', (route) => route.fulfill({ json: { session_id: active.session_id, status: 'ended' } }))
  await page.goto('/therapy/5')
  await page.getByRole('button', { name: 'Break or stop' }).click()
  await expect.poll(() => typeof releasePause).toBe('function')
  await page.getByRole('button', { name: 'End session' }).click()
  await expect(page.getByRole('heading', { name: 'Session ended' }).first()).toBeVisible()
  releasePause()
  await expect.poll(() => pauseSettled).toBe(true)
  await expect(page.getByText('Practice paused')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Start recording' })).toHaveCount(0)
})
