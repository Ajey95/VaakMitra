import { expect, test } from '@playwright/test'

const USER = {
  id: 'browser-test-child',
  email: 'browser-test@example.invalid',
  full_name: 'Browser Test Parent',
  child_name: 'Maya',
  child_age: 7,
  role: 'user',
  total_stars: 12,
}

async function mockPrivateApi(page) {
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(USER) })
    if (path === '/api/interactive-sessions/summary') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        sessions_this_week: 0,
        communication_turns: 0,
        independent_percentage: 0,
        most_practised_activity: null,
        assistance_trend: [],
        recommendation: 'Complete a Play & Practice activity to begin the private progress summary.',
      }) })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
}

async function expectNoHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
}

test.beforeEach(async ({ page }) => {
  await mockPrivateApi(page)
})

test('activity home has six named destinations, keyboard access, and large targets', async ({ page }) => {
  await page.goto('/play')
  await expect(page.getByRole('heading', { name: 'What would you like to play?' })).toBeVisible()
  const cards = page.locator('.play-card')
  await expect(cards).toHaveCount(6)
  await expect(page.getByRole('button', { name: /Breath Balloon/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /River Rescue/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Mouth Mirror/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Play with Pippin/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Talk Together/ })).toBeVisible()
  await page.keyboard.press('Tab')
  expect(await page.evaluate(() => document.activeElement !== document.body)).toBe(true)
  const boxes = await cards.evaluateAll((items) => items.map((item) => item.getBoundingClientRect()).map(({ width, height }) => ({ width, height })))
  for (const box of boxes) expect(Math.min(box.width, box.height)).toBeGreaterThanOrEqual(44)
  await expectNoHorizontalOverflow(page)
})

test('system reduced motion and calm/pause controls are effective', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/play/together')
  await expect(page.locator('html')).toHaveAttribute('data-interaction-motion', 'reduced')
  const calm = page.getByRole('button', { name: 'Calm' })
  await calm.click()
  await expect(calm).toHaveAttribute('aria-pressed', 'true')
  await expect(page.locator('html')).toHaveAttribute('data-interaction-motion', 'minimal')
  await page.getByRole('button', { name: 'Pause activity' }).click()
  await expect(page.getByText('Activity paused')).toBeVisible()
  await page.getByRole('button', { name: 'Keep playing' }).click()
  await expect(page.getByText('Mission 1 of 5')).toBeVisible()
})

test('microphone denial and camera-free practice never block a child', async ({ page, context }) => {
  await context.clearPermissions()
  await page.goto('/play/arcade/breath-balloon')
  await page.getByRole('button', { name: 'Check my microphone' }).click()
  await expect(page.getByText('The microphone is off', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Use screen control' })).toBeVisible()

  await page.goto('/play/mouth-mirror')
  await page.getByRole('button', { name: 'Model only' }).click()
  await expect(page.getByText('No camera is running')).toBeVisible()
  await expect(page.locator('.mirror-camera__live')).toHaveCount(0)
})

test('child experiences fit a narrow mobile viewport without sideways scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  for (const path of ['/play', '/play/quest/river-rescue', '/play/pippin', '/play/together']) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    await expectNoHorizontalOverflow(page)
    await expect(page.locator('h1').first()).toBeVisible()
  }
})

test('leaving a live microphone activity stops every media track and stores no transcript', async ({ page }) => {
  await page.addInitScript(() => {
    window.__stoppedTracks = 0
    const track = { stop: () => { window.__stoppedTracks += 1 } }
    const stream = { getTracks: () => [track] }
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: async () => stream } })
    class MockMediaRecorder {
      constructor() { this.state = 'inactive'; this.ondataavailable = null; this.onstop = null }
      start() { this.state = 'recording' }
      stop() { this.state = 'inactive'; this.ondataavailable?.({ data: new Blob(['x']), size: 1 }); this.onstop?.() }
    }
    window.MediaRecorder = MockMediaRecorder
  })
  await page.goto('/play/arcade/breath-balloon')
  await page.getByRole('button', { name: 'Check my microphone' }).click()
  await expect(page.getByText('Listening to the room')).toBeVisible()
  await page.getByRole('button', { name: 'Exit activity' }).click()
  await expect(page).toHaveURL(/\/play$/)
  expect(await page.evaluate(() => window.__stoppedTracks)).toBeGreaterThan(0)
  const saved = await page.evaluate(() => JSON.stringify({ ...localStorage }))
  expect(saved).not.toMatch(/transcript|audioBlob|video|frames/i)
})

test('the four upgraded games expose their animated scene states while Pippin stays available', async ({ page }) => {
  await page.goto('/play/arcade/breath-balloon')
  await expect(page.locator('.breath-card')).toBeVisible()

  await page.goto('/play/quest/river-rescue')
  await expect(page.locator('[data-testid="kavi-picture-scene"]')).toHaveAttribute('data-mood', 'idle')
  await expect(page.locator('.kavi-river-effects')).toBeVisible()

  await page.goto('/play/mouth-mirror')
  await page.getByRole('button', { name: 'Model only' }).click()
  await expect(page.locator('.mouth-guide')).toHaveAttribute('data-visual-state', 'model')

  await page.goto('/play/together')
  await expect(page.locator('.together-environment')).toHaveAttribute('data-environment', 'kitchen')

  await page.goto('/play/pippin')
  await expect(page.getByRole('heading', { name: /Talk with Pippin/ })).toBeVisible()
})
