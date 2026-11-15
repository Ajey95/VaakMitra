import { expect, test } from '@playwright/test'

test.use({ channel: 'msedge' })

const evidenceDir = 'C:/Users/AJEYA/.codex/visualizations/2026/09/11/01a09207-2ae3-7ba1-a2e7-758f8ac4acb9'

test('rpt001 ux009 empty report view never shows inherited mock scores or camera metrics', async ({ page }) => {
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/v1/word-session-reports', (route) => route.fulfill({ json: { reports: [] } }))
  await page.goto('/reports')
  await expect(page.getByText('No word-session report yet')).toBeVisible()
  await expect(page.getByText('87%')).toHaveCount(0)
  await expect(page.getByText('Camera Time')).toHaveCount(0)
  await expect(page.getByText('Top 12% of peers')).toHaveCount(0)
})

test('rpt001 002 report shows real Tamil word trajectory and voluntary break', async ({ page }) => {
  const runtimeErrors = []
  page.on('pageerror', (error) => runtimeErrors.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') runtimeErrors.push(message.text()) })
  const report = {
    schema_version: 'word-session-report-1', session_id: 'SES-TEST', status: 'ended', review_status: 'not_signed',
    metrics: { planned_words: 2, attempted_words: 2, scoreable_words: 2, first_scoreable_pass_words: 1,
      eventual_pass_words: 2, total_captures: 4, unscorable_attempts: 1, voluntary_breaks: 1 },
    word_labels: { TA_WORD_0001: 'அம்மா', TA_WORD_0002: 'அப்பா' },
    timeline: [
      { ordinal: 1, word_id: 'TA_WORD_0001', decision: 'RETRY', reason_code: 'CALIBRATED_WORD_MISMATCH' },
      { ordinal: 2, word_id: 'TA_WORD_0001', decision: 'PASS', reason_code: 'CALIBRATED_TARGET_MATCH' },
      { ordinal: 3, word_id: 'TA_WORD_0002', decision: 'UNSCORABLE', reason_code: 'INVALID_AUDIO' },
      { ordinal: 4, word_id: 'TA_WORD_0002', decision: 'PASS', reason_code: 'CALIBRATED_TARGET_MATCH' },
    ],
    break_data_status: 'recorded',
    session_events: [{ type: 'break_started', reason: 'user_pause', session_second: 30 },
      { type: 'break_ended', reason: 'user_pause', session_second: 60 }],
  }
  await page.route('**/api/auth/me', (route) => route.fulfill({ json: { _id: 'SYNTHETIC-CHILD', role: 'user' } }))
  await page.route('**/api/v1/word-session-reports', (route) => route.fulfill({ json: { reports: [report] } }))
  await page.goto('/reports')
  await expect(page.getByText('அம்மா').first()).toBeVisible()
  await expect(page.getByText('அப்பா').first()).toBeVisible()
  await expect(page.getByText('Break started at 0:30')).toBeVisible()
  await expect(page.getByText('First scoreable word passes')).toBeVisible()
  await expect(page.getByText('Therapist review not signed')).toBeVisible()
  await page.screenshot({ path: `${evidenceDir}/synthetic-report-desktop.png`, fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByText('Break started at 0:30')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: `${evidenceDir}/synthetic-report-mobile.png`, fullPage: true })
  expect(runtimeErrors).toEqual([])
})
