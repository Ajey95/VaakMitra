import { expect, test } from '@playwright/test'

test('dec008 keeps live blockers distinct from simulated avatar outcomes', async ({ page }) => {
  let assessmentCalls = 0
  await page.route('**/api/auth/me', (route) => route.fulfill({ status: 401, contentType: 'application/json', body: '{"detail":"Not authenticated"}' }))
  await page.route('**/health/live', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"status":"ok"}' }))
  await page.route('**/health/ready', (route) => route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"database_unavailable"}' }))
  await page.route('**/health/scoring', (route) => route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":{"ready":false,"reasons":["bundle_config_unavailable"]}}' }))
  await page.route('**/api/v1/vocabulary', (route) => route.fulfill({ status: 401, contentType: 'application/json', body: '{"detail":"Not authenticated"}' }))
  await page.route('**/api/v1/word-assessments', (route) => { assessmentCalls += 1; return route.fulfill({ status: 500 }) })

  await page.goto('/dev/backend-lab')
  await expect(page.getByText('ENGINEERING ONLY')).toBeVisible()
  await page.getByRole('button', { name: 'Run live check' }).click()
  await expect(page.locator('.lab-reason strong')).toHaveText('bundle_config_unavailable')
  await expect(page.getByText('Authentication required')).toBeVisible()
  await page.getByLabel('Simulated decision').selectOption('capability')
  await expect(page.getByText('SIMULATED — NO BACKEND CALL')).toBeVisible()
  await expect(page.getByText('MODEL_UNAVAILABLE')).toBeVisible()
  expect(assessmentCalls).toBe(0)
})

test('dec016 displays registry availability without enabling scoring for an inactive word', async ({ page }) => {
  await page.route('**/api/auth/me', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"_id":"OP-1","role":"admin"}' }))
  await page.route('**/health/**', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"status":"ready"}' }))
  await page.route('**/api/v1/vocabulary', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    vocabulary_version: 'ta-words-v1.0.0', entries: [
      { word_id: 'TA_WORD_0001', canonical_tamil: 'அம்மா', state: 'intended', available_for_scoring: false },
      { word_id: 'TA_WORD_0002', canonical_tamil: 'அப்பா', state: 'active', available_for_scoring: true },
    ],
  }) }))
  await page.goto('/dev/backend-lab')
  await page.getByRole('button', { name: 'Run live check' }).click()
  await expect(page.getByText('1 scoreable / 2 listed')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Open local test session' })).toBeDisabled()
})

test('prv002 lab cannot attach adult diagnostic audio to a child plan', async ({ page }) => {
  let sessions = 0
  let assessments = 0
  await page.route('**/api/auth/me', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"_id":"OP-1","role":"admin"}' }))
  await page.route('**/health/**', (route) => route.fulfill({ status: 200, body: '{}' }))
  await page.route('**/api/v1/vocabulary', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"vocabulary_version":"ta-words-v1.0.0","entries":[]}' }))
  await page.route('**/api/v1/word-sessions', (route) => { sessions += 1; return route.fulfill({ status: 500 }) })
  await page.route('**/api/v1/word-assessments', (route) => { assessments += 1; return route.fulfill({ status: 500 }) })
  await page.goto('/dev/backend-lab')
  await page.getByRole('button', { name: 'Run live check' }).click()
  await expect(page.getByLabel('Assigned plan ID')).toHaveCount(0)
  await expect(page.locator('input[type="file"]')).toHaveCount(0)
  expect(sessions).toBe(0)
  expect(assessments).toBe(0)
})

test('ux007 keeps an exit and readable layout on a small phone viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route('**/api/auth/me', (route) => route.fulfill({ status: 401, body: '{}' }))
  await page.goto('/dev/backend-lab')
  await expect(page.getByRole('link', { name: 'VaakMitra' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
})

test('dec018 adult WAV diagnostics use only the isolated namespace', async ({ page }) => {
  let childCalls = 0
  let adultCalls = 0
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/api/auth/me', route => route.fulfill({ status: 401, body: '{}' }))
  await page.route('**/api/v1/word-**', route => { childCalls++; return route.fulfill({ status: 500 }) })
  await page.route('**/api/dev/word-lab/open', route => route.fulfill({ json: { status: 'open' } }))
  await page.route('**/api/dev/word-lab/close', route => route.fulfill({ json: { status: 'closed' } }))
  await page.route('**/api/dev/word-lab/status', route => route.fulfill({ json: {
    state: 'ready', pipeline_ready: true, scoring_ready: false, words: [{ word_id: 'W1', target_word: 'அம்மா' }],
  } }))
  await page.route('**/api/dev/word-lab/assess', route => { adultCalls++; return route.fulfill({ json: {
    evidence_scope: 'real_adult_engineering', scoring_ready: false, persisted: false,
    adult_preview: adultCalls === 1
      ? { status: 'provisional', estimate: 0.87, reason_code: 'adult_engineering_only' }
      : { status: 'unavailable', estimate: null, reason_code: 'INSUFFICIENT_EVIDENCE' },
    development_result: adultCalls === 1
      ? { schema_version: 'adult-development-decision-1', decision: 'DEV_MATCH', estimate: 0.87,
        reason_code: 'adult_engineering_demonstration_only', avatar_state: 'CELEBRATE',
        band_version: 'adult-dev-bands-1', retry_max: 0.35, match_min: 0.85 }
      : { schema_version: 'adult-development-decision-1', decision: 'DEV_UNAVAILABLE', estimate: null,
        reason_code: 'INSUFFICIENT_EVIDENCE', avatar_state: 'RECAPTURE',
        band_version: 'adult-dev-bands-1', retry_max: 0.35, match_min: 0.85 },
    result: { word_id: 'W1', target_word: 'அம்மா', decision: 'UNSCORABLE', word_match_probability: null,
      reason_code: 'CALIBRATION_UNAVAILABLE', avatar_state: 'BREAK',
      observed_candidates: adultCalls === 1 ? [{ word: 'அம்மா', probability: 0.92 }] : [],
      quality: { valid: true, vad_mode: 'onnx_cpu', speech_detected: true, snr_acceptable: true,
        clipped: false, duration_s: 1.1, speech_duration_s: 0.8, reason: null },
      evidence: { original_asr: { available: true, target_probability: 1 },
        normalized_asr: { available: true, target_probability: 0.9 },
        word_classifier: { available: true, target_probability: 0.5 },
        embedding_dtw: { available: true, similarity: 0.7 } },
      latency_ms: 123, calibration_version: 'test-fixture-unapproved' },
  } }) })
  await page.route('**/api/dev/word-lab/session-checks', route => route.fulfill({ json: {
    passed: true, checks: [{ name: 'Stop suppresses late results', passed: true }],
  } }))
  await page.goto('/dev/backend-lab')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Open local test session' }).click()
  await expect(page.getByText('Model: ready')).toBeVisible()
  await page.getByLabel('Adult WAV (optional)', { exact: true }).setInputFiles({ name: 'adult.wav', mimeType: 'audio/wav', buffer: Buffer.from('fixture') })
  await page.getByRole('button', { name: 'Run real audio test' }).click()
  await expect(page.getByLabel('Real audio result')).toContainText('Development result: MATCH')
  await expect(page.getByLabel('Real audio result')).not.toContainText('UNSCORABLE')
  await expect(page.getByLabel('Real audio result')).toContainText('87%')
  await expect(page.getByLabel('Real audio result')).toContainText('Provisional adult match estimate')
  await expect(page.getByLabel('Real audio result')).toContainText('Model candidate')
  await expect(page.getByLabel('Real audio result')).toContainText('Speech detected')
  await expect(page.getByLabel('Real audio result')).toContainText('1.1 s')
  await expect(page.getByLabel('Real audio result')).toContainText('No child score or pronunciation diagnosis')
  await page.getByRole('button', { name: 'Run real audio test' }).click()
  await expect(page.getByLabel('Real audio result')).toContainText('Development result: RECORD AGAIN')
  await expect(page.getByLabel('Real audio result')).toContainText('No estimate')
  await expect(page.getByLabel('Real audio result')).toContainText('No model candidate')
  await expect(page.getByLabel('Real audio result')).not.toContainText('87%')
  await page.getByRole('button', { name: 'Run session checks' }).click()
  await expect(page.getByLabel('Session checks')).toContainText('Stop suppresses late results')
  await page.getByRole('button', { name: 'Stop / clear audio' }).click()
  await expect(page.getByLabel('Real audio result')).toHaveCount(0)
  await page.getByRole('button', { name: 'Close test session' }).click()
  await expect(page.getByRole('button', { name: 'Open local test session' })).toBeVisible()
  expect(childCalls).toBe(0)
  expect(errors).toEqual([])
})

test('prv002 an authenticated child account cannot use operator diagnostics', async ({ page }) => {
  await page.route('**/api/auth/me', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"_id":"USER-1","role":"user"}' }))
  await page.route('**/health/**', (route) => route.fulfill({ status: 200, body: '{}' }))
  await page.route('**/api/v1/vocabulary', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"vocabulary_version":"ta-words-v1.0.0","entries":[]}' }))
  await page.goto('/dev/backend-lab')
  await page.getByRole('button', { name: 'Run live check' }).click()
  await expect(page.getByText('Operator authorization required')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Open local test session' })).toBeDisabled()
})

test('dec025 live avatar automatically prompts listens coaches retries and stops capture', async ({ page }) => {
  test.setTimeout(60_000)
  let adultCalls = 0
  await page.addInitScript(() => {
    window.__avatarHarness = { spoken: [], tracks: [], processors: [] }
    window.SpeechSynthesisUtterance = class {
      constructor(text) { this.text = text; this.lang = ''; this.voice = null }
    }
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
      getVoices: () => [{ name: 'Local Tamil', lang: 'ta-IN', localService: true }],
      addEventListener: () => {}, removeEventListener: () => {},
      cancel: () => { window.__avatarHarness.cancelled = (window.__avatarHarness.cancelled || 0) + 1 },
      speak: (utterance) => {
        window.__avatarHarness.spoken.push(utterance.text)
        utterance.onstart?.()
        setTimeout(() => utterance.onend?.(), 10)
      },
    } })
    const originalProcessor = AudioContext.prototype.createScriptProcessor
    AudioContext.prototype.createScriptProcessor = function (...args) {
      const processor = originalProcessor.apply(this, args)
      window.__avatarHarness.processors.push(processor)
      window.__avatarHarness.processor = processor
      return processor
    }
    navigator.mediaDevices.getUserMedia = async () => {
      const context = new AudioContext()
      const destination = context.createMediaStreamDestination()
      const track = destination.stream.getAudioTracks()[0]
      const stop = track.stop.bind(track)
      track.stop = () => { stop(); context.close() }
      window.__avatarHarness.tracks.push(track)
      return destination.stream
    }
  })
  await page.route('**/api/auth/me', route => route.fulfill({ status: 401, body: '{}' }))
  await page.route('**/api/v1/word-**', route => route.fulfill({ status: 500 }))
  await page.route('**/api/dev/word-lab/open', route => route.fulfill({ json: { status: 'open' } }))
  await page.route('**/api/dev/word-lab/close', route => route.fulfill({ json: { status: 'closed' } }))
  await page.route('**/api/dev/word-lab/status', route => route.fulfill({ json: {
    state: 'ready', pipeline_ready: true, scoring_ready: false, words: [{ word_id: 'W1', target_word: 'அம்மா' }],
  } }))
  await page.route('**/api/dev/word-lab/assess', route => {
    adultCalls += 1
    const retry = adultCalls === 1
    return route.fulfill({ json: {
      evidence_scope: 'real_adult_engineering', scoring_ready: false, persisted: false,
      adult_preview: { status: 'provisional', estimate: retry ? 0.22 : 0.94, reason_code: 'adult_engineering_only' },
      development_result: { schema_version: 'adult-development-decision-1', decision: retry ? 'DEV_TRY_AGAIN' : 'DEV_MATCH',
        estimate: retry ? 0.22 : 0.94, reason_code: 'adult_engineering_demonstration_only',
        avatar_state: retry ? 'ENCOURAGE_RETRY' : 'CELEBRATE', band_version: 'adult-dev-bands-1', retry_max: 0.35, match_min: 0.85 },
      chunk_coach: { status: 'text_hypothesis', target_word: 'அம்மா', chunks: ['அம்', 'மா'], focus_index: 1 },
      result: { word_id: 'W1', target_word: 'அம்மா', decision: 'UNSCORABLE', reason_code: 'CALIBRATION_UNAVAILABLE',
        avatar_state: 'BREAK', observed_candidates: [{ word: retry ? 'அம்ம' : 'அம்மா', probability: 0.9 }],
        quality: { valid: true, vad_mode: 'onnx_cpu', speech_detected: true, duration_s: 1 },
        evidence: { original_asr: { target_probability: retry ? 0 : 1 }, word_classifier: { target_probability: 0.8 }, embedding_dtw: { similarity: 0.8 } },
        latency_ms: 100, calibration_version: 'test' },
    } })
  })

  await page.goto('/dev/backend-lab')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Open local test session' }).click()
  await page.getByRole('button', { name: 'Start live practice' }).click()
  await expect(page.getByLabel('Interactive avatar coach')).toHaveAttribute('data-avatar-phase', 'LISTENING')

  const completeSpokenWord = async () => {
    await page.waitForTimeout(220)
    await page.evaluate(() => {
    const loud = new Float32Array(4096).fill(0.22)
    const quiet = new Float32Array(4096)
    for (let index = 0; index < 3; index += 1) window.__avatarHarness.processor.onaudioprocess({ inputBuffer: { getChannelData: () => loud } })
    for (let index = 0; index < 9; index += 1) window.__avatarHarness.processor.onaudioprocess({ inputBuffer: { getChannelData: () => quiet } })
    })
  }
  await completeSpokenWord()
  await expect.poll(() => adultCalls).toBe(1)
  await expect(page.getByLabel('Interactive avatar coach')).toHaveAttribute('data-avatar-phase', 'LISTENING')
  await completeSpokenWord()
  await expect.poll(() => adultCalls).toBe(2)
  await expect(page.getByLabel('Interactive avatar coach')).toHaveAttribute('data-avatar-phase', 'PRAISE')
  expect(await page.evaluate(() => window.__avatarHarness.spoken)).toEqual(expect.arrayContaining(['அம்மா', 'மா', 'மிக நன்று!']))
  expect(await page.evaluate(() => window.__avatarHarness.tracks.every(track => track.readyState === 'ended'))).toBe(true)

  await page.getByRole('button', { name: 'Start live practice' }).click()
  await expect(page.getByLabel('Interactive avatar coach')).toHaveAttribute('data-avatar-phase', 'LISTENING')
  await page.getByRole('button', { name: 'Stop live practice' }).click()
  await expect(page.getByLabel('Interactive avatar coach')).toHaveAttribute('data-avatar-phase', 'IDLE')
  expect(await page.evaluate(() => window.__avatarHarness.tracks.at(-1).readyState)).toBe('ended')
})

test('dec018 dec022 adult microphone records a WAV only in the local lab and releases capture', async ({ page }) => {
  test.setTimeout(60000)
  let adultCalls = 0
  let childCalls = 0
  let wavBytes = null
  await page.addInitScript(() => {
    window.__labCapture = { tracks: [] }
    const originalProcessor = AudioContext.prototype.createScriptProcessor
    AudioContext.prototype.createScriptProcessor = function (...args) {
      const processor = originalProcessor.apply(this, args)
      window.__labCapture.processor = processor
      return processor
    }
    navigator.mediaDevices.getUserMedia = async () => {
      const context = new AudioContext()
      const destination = context.createMediaStreamDestination()
      const track = destination.stream.getAudioTracks()[0]
      const stop = track.stop.bind(track)
      track.stop = () => { stop(); context.close() }
      window.__labCapture.tracks.push(track)
      return destination.stream
    }
  })
  await page.route('**/api/auth/me', route => route.fulfill({ status: 401, body: '{}' }))
  await page.route('**/api/v1/word-**', route => { childCalls++; return route.fulfill({ status: 500 }) })
  await page.route('**/api/dev/word-lab/open', route => route.fulfill({ json: { status: 'open' } }))
  await page.route('**/api/dev/word-lab/close', route => route.fulfill({ json: { status: 'closed' } }))
  await page.route('**/api/dev/word-lab/status', route => route.fulfill({ json: {
    state: 'ready', pipeline_ready: true, words: [{ word_id: 'W1', target_word: 'அம்மா' }],
  } }))
  await page.route('**/api/dev/word-lab/assess', route => {
    adultCalls++
    wavBytes = route.request().postDataBuffer()
    return route.fulfill({ json: {
      adult_preview: { status: 'unavailable', estimate: null, reason_code: 'INSUFFICIENT_EVIDENCE' },
      development_result: { schema_version: 'adult-development-decision-1', decision: 'DEV_UNAVAILABLE',
        estimate: null, reason_code: 'INSUFFICIENT_EVIDENCE', avatar_state: 'RECAPTURE',
        band_version: 'adult-dev-bands-1', retry_max: 0.35, match_min: 0.85 },
      result: { decision: 'UNSCORABLE', reason_code: 'CALIBRATION_UNAVAILABLE', avatar_state: 'BREAK',
        evidence: { original_asr: {}, word_classifier: {}, embedding_dtw: {} }, latency_ms: 123, calibration_version: 'test' },
    } })
  })
  await page.goto('/dev/backend-lab')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Open local test session' }).click()
  await page.getByRole('button', { name: 'Record adult mic' }).click()
  await expect(page.getByText('Microphone recording')).toBeVisible()
  await page.evaluate(() => window.__labCapture.processor.onaudioprocess({
    inputBuffer: { getChannelData: () => new Float32Array(4096).fill(0.25) },
  }))
  await page.waitForTimeout(250)
  await page.getByRole('button', { name: 'Stop & test' }).click()
  await expect(page.getByLabel('Real audio result')).toContainText('Development result: RECORD AGAIN')
  await expect(page.getByLabel('Real audio result')).not.toContainText('UNSCORABLE')
  expect(wavBytes.toString('latin1')).toContain('RIFF')
  expect(wavBytes.toString('latin1')).toContain('WAVE')
  expect(adultCalls).toBe(1)
  expect(childCalls).toBe(0)
  expect(await page.evaluate(() => window.__labCapture.tracks[0].readyState)).toBe('ended')
  await page.getByRole('button', { name: 'Record adult mic' }).click()
  await page.getByRole('button', { name: 'Cancel recording' }).click()
  expect(await page.evaluate(() => window.__labCapture.tracks[1].readyState)).toBe('ended')
  expect(adultCalls).toBe(1)
  await page.getByRole('button', { name: 'Record adult mic' }).click()
  await page.getByRole('button', { name: 'Close test session' }).click()
  expect(await page.evaluate(() => window.__labCapture.tracks[2].readyState)).toBe('ended')
  expect(adultCalls).toBe(1)
  await page.getByRole('button', { name: 'Open local test session' }).click()
  await page.evaluate(() => {
    AudioContext.prototype.createScriptProcessor = function () {
      window.__labCapture.failedContext = this
      throw new Error('audio graph unavailable')
    }
  })
  await page.getByRole('button', { name: 'Record adult mic' }).click()
  await expect(page.getByRole('alert')).toContainText('audio graph unavailable')
  expect(await page.evaluate(() => window.__labCapture.tracks[3].readyState)).toBe('ended')
  expect(await page.evaluate(() => window.__labCapture.failedContext.state)).toBe('closed')
})
