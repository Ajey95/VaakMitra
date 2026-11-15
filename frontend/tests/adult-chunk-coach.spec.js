import { expect, test } from '@playwright/test'

test('dec023 dec024 adult lab acts on a dev retry and rehearses without child routes', async ({ page }) => {
  let adultCalls = 0
  let childCalls = 0
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.route('**/api/auth/me', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"_id":"OP-1","role":"admin"}' }))
  await page.route('**/health/**', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '{"status":"ready"}' }))
  await page.route('**/api/v1/vocabulary', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    vocabulary_version: 'ta-words-v1.0.0', entries: [{ word_id: 'W1', canonical_tamil: 'அம்மா', state: 'active', available_for_scoring: true }],
  }) }))
  await page.route('**/api/v1/word-**', (route) => { childCalls++; return route.fulfill({ status: 500 }) })
  await page.route('**/api/dev/word-lab/open', (route) => route.fulfill({ json: { status: 'open' } }))
  await page.route('**/api/dev/word-lab/close', (route) => route.fulfill({ json: { status: 'closed' } }))
  await page.route('**/api/dev/word-lab/status', (route) => route.fulfill({ json: {
    state: 'ready', pipeline_ready: true, words: [{ word_id: 'W1', target_word: 'அம்மா' }],
  } }))
  await page.route('**/api/dev/word-lab/assess', (route) => {
    adultCalls++
    return route.fulfill({ json: {
      evidence_scope: 'real_adult_engineering', persisted: false, scoring_ready: false,
      adult_preview: { status: 'provisional', estimate: .2, reason_code: 'adult_engineering_only' },
      development_result: { schema_version: 'adult-development-decision-1', decision: 'DEV_TRY_AGAIN',
        estimate: .2, reason_code: 'adult_engineering_demonstration_only', avatar_state: 'ENCOURAGE_RETRY',
        band_version: 'adult-dev-bands-1', retry_max: .35, match_min: .85 },
      chunk_coach: { status: 'text_hypothesis', target_word: 'அம்மா', chunks: ['அம்', 'மா'],
        focus_index: 1, focus_position: 'end', basis: 'unvalidated_asr_text_difference' },
      result: { target_word: 'அம்மா', decision: 'UNSCORABLE', word_match_probability: null,
        reason_code: 'CALIBRATION_UNAVAILABLE', avatar_state: 'BREAK',
        observed_candidates: [{ word: 'அம்மி', probability: .8 }],
        quality: { valid: true, speech_detected: true, duration_s: 1.2 },
        evidence: { original_asr: {}, normalized_asr: {}, word_classifier: {}, embedding_dtw: {} },
        latency_ms: 200, calibration_version: 'adult-only' },
    } })
  })
  await page.goto('/dev/backend-lab')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Open local test session' }).click()
  await page.getByLabel('Adult WAV (optional)', { exact: true }).setInputFiles({
    name: 'adult.wav', mimeType: 'audio/wav', buffer: Buffer.from('fixture'),
  })
  await page.getByRole('button', { name: 'Run real audio test' }).click()
  const result = page.getByLabel('Real audio result')
  await expect(result).toContainText('Development result')
  await expect(result).toContainText('TRY AGAIN')
  await expect(result).not.toContainText('UNSCORABLE')
  const coach = page.getByLabel('Adult visual chunk coach')
  await expect(coach).toContainText('unvalidated ASR text hypothesis')
  await expect(coach).toContainText('ending')
  await expect(coach).toContainText('அம்')
  await expect(coach).toContainText('மா')
  await coach.getByRole('button', { name: 'Focus chunk 1: அம்' }).click()
  await expect(coach).toContainText('manually selected')
  await coach.getByRole('button', { name: 'I tried this chunk' }).click()
  await expect(coach).toContainText('Blend the chunks')
  await coach.getByRole('button', { name: 'I blended the word' }).click()
  await expect(coach).toContainText('Now try the whole word again')
  await coach.getByRole('button', { name: 'Go to whole-word recording' }).click()
  await expect(page.getByRole('button', { name: 'Record adult mic' })).toBeFocused()
  await page.getByRole('button', { name: 'Run real audio test' }).click()
  await expect(coach).toContainText('Coached cycle 2 of 2')
  await coach.getByRole('button', { name: 'I tried this chunk' }).click()
  await coach.getByRole('button', { name: 'I blended the word' }).click()
  await page.getByRole('button', { name: 'Run real audio test' }).click()
  await expect(coach).toContainText('Time for a break')
  expect(adultCalls).toBe(3)
  expect(childCalls).toBe(0)
  await page.getByRole('button', { name: 'Stop / clear audio' }).click()
  await expect(coach).toHaveCount(0)
  await page.getByRole('button', { name: 'Close test session' }).click()
  expect(errors).toEqual([])
})
