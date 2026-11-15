import { expect, test } from '@playwright/test'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

test('chk003 caregiver sees real overdue reminder and requests assigned-therapist checkup', async ({ page }) => {
  let requests = 0
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') return route.fulfill({ json: {
      _id: '0000000000000000000000c1', full_name: 'Caregiver', child_name: 'Kavi', role: 'user',
    } })
    if (path === '/api/appointments/checkup-status') return route.fulfill({ json: {
      state: requests ? 'overdue' : 'overdue', due_at: '2026-09-14T10:00:00+00:00',
      practice_available: true,
      appointment: requests ? { id: 'checkup-1', status: 'pending', scheduled_at: '2026-09-16T10:00:00+00:00' } : null,
    } })
    if (path === '/api/appointments/available-therapists') return route.fulfill({ json: [
      { _id: '0000000000000000000000d1', full_name: 'Assigned Therapist' },
    ] })
    if (path === '/api/appointments' && route.request().method() === 'GET') return route.fulfill({ json: {
      items: requests ? [{ id: 'checkup-1', kind: 'checkup', status: 'pending', therapist_name: 'Assigned Therapist',
        therapist_id: '0000000000000000000000d1', scheduled_at: '2026-09-16T10:00:00+00:00', mode: 'online' }] : [],
      total: requests,
    } })
    if (path === '/api/appointments/checkups' && route.request().method() === 'POST') {
      requests++
      const payload = route.request().postDataJSON()
      expect(payload).not.toHaveProperty('therapist_id')
      return route.fulfill({ json: { id: 'checkup-1', status: 'pending', kind: 'checkup' } })
    }
    return route.fulfill({ status: 404, json: { detail: 'not found' } })
  })
  await page.goto('/appointments')
  await expect(page.getByText('Checkup overdue')).toBeVisible()
  await expect(page.getByText('Practice remains available')).toBeVisible()
  await expect(page.getByText('Dr. Anitha Raman')).toHaveCount(0)
  await page.getByRole('button', { name: 'Request checkup' }).click()
  await page.getByLabel('Date and time').fill('2026-09-16T10:00')
  await page.getByRole('button', { name: 'Send request' }).click()
  await expect(page.getByText('Request pending')).toBeVisible()
  expect(requests).toBe(1)
  await page.screenshot({ path: join(tmpdir(), 'vaakmitra-checkup-reviewed-2026-09-14.png'), fullPage: true })
})

test('gov007 parent dashboard has no fictional child or clinical notes', async ({ page }) => {
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') return route.fulfill({ json: {
      _id: '0000000000000000000000c1', full_name: 'Caregiver', child_name: 'Kavi', role: 'user',
    } })
    if (path === '/api/appointments/checkup-status') return route.fulfill({ json: {
      state: 'schedule_unestablished', due_at: null, practice_available: true, appointment: null,
    } })
    return route.fulfill({ json: {} })
  })
  await page.goto('/parent')
  await expect(page.getByRole('heading', { name: "Kavi's practice" })).toBeVisible()
  await expect(page.getByText('Arjun Kumar')).toHaveCount(0)
  await expect(page.getByText('Dr. Priya Raman')).toHaveCount(0)
  await expect(page.getByText('Schedule a therapist checkup')).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: join(tmpdir(), 'vaakmitra-parent-mobile-2026-09-14.png'), fullPage: true })
})

test('gov005 verified therapist can record an exact-hash review decision', async ({ page }) => {
  let reviewed = false
  const hash = 'a'.repeat(64)
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') return route.fulfill({ json: {
      _id: '0000000000000000000000d1', full_name: 'Reviewing Therapist', role: 'therapist',
    } })
    if (path === '/api/therapist/children') return route.fulfill({ json: { children: [], count: 0 } })
    if (path === '/api/governance/batches') return route.fulfill({ json: { items: [{
      id: 'batch-1', kind: 'reference', manifest_sha256: 'b'.repeat(64), item_count: 1,
      reviewed_count: reviewed ? 1 : 0, status: reviewed ? 'reviewed_pending_export' : 'pending_review',
    }] } })
    if (path === '/api/governance/batches/batch-1' && route.request().method() === 'GET') return route.fulfill({ json: {
      batch: { id: 'batch-1', kind: 'reference', items: [{ item_id: 'source-1', word_id: 'TA_WORD_0001', audio_sha256: hash }] },
      decisions: reviewed ? [{ item_id: 'source-1', decision: 'approved' }] : [],
    } })
    if (path === '/api/governance/batches/batch-1/decisions') {
      const payload = route.request().postDataJSON()
      expect(payload).toEqual({ item_id: 'source-1', observed_sha256: hash, decision: 'approved', capture_valid: true, quality_score: 0.8 })
      reviewed = true
      return route.fulfill({ json: { item_id: 'source-1', decision: 'approved' } })
    }
    return route.fulfill({ json: {} })
  })
  await page.goto('/therapist')
  await expect(page.getByText('Human review queue')).toBeVisible()
  await page.getByRole('button', { name: 'Open reference review' }).click()
  await expect(page.getByText('source-1')).toBeVisible()
  await page.getByLabel('Observed SHA-256').fill(hash)
  await page.getByLabel('Quality score').fill('0.8')
  await page.getByLabel('I reviewed the source outside the app').check()
  await page.getByRole('button', { name: 'Approve item' }).click()
  await expect(page.getByText('Reviewed 1 of 1')).toBeVisible()
  expect(reviewed).toBe(true)
})
