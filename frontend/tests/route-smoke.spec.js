import { expect, test } from '@playwright/test'

const ROUTES = [
  '/', '/login', '/register', '/admin-login', '/forgot-password', '/verify-otp',
  '/dashboard', '/training', '/assessment', '/letter-learning', '/videos',
  '/speech-analysis', '/tongue-tracking', '/games', '/progress', '/reports',
  '/achievements', '/rewards', '/calendar', '/notifications', '/appointments',
  '/parent', '/therapist', '/profile', '/settings', '/help', '/feedback', '/about',
  '/play', '/play/settings', '/play/arcade/breath-balloon', '/play/quest/river-rescue',
  '/play/mouth-mirror', '/play/pippin', '/play/together', '/therapy/3', '/admin',
]

const USER = {
  id: 'route-audit-admin',
  email: 'route-audit@example.invalid',
  full_name: 'Route Audit User',
  child_name: 'Kavi',
  child_age: 7,
  language: 'Tamil',
  role: 'admin',
  total_sessions: 12,
  total_stars: 180,
}

test('every application route renders without a broken image or redirect loop', async ({ page }) => {
  test.setTimeout(180_000)
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(USER) })
    }
    if (path === '/api/therapy/lessons/3') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 3, symbol: 'ல', english: 'LA', phoneme: 'la', type: 'letter', difficulty: 2 }),
      })
    }
    return route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"route audit backend unavailable"}' })
  })

  for (const route of ROUTES) {
    await page.goto(route, { waitUntil: 'domcontentloaded' })
    await expect(page.locator('body')).not.toBeEmpty()
    await expect(page.locator('.app-loading')).toHaveCount(0)
    if (!['/login', '/register', '/admin-login', '/forgot-password', '/verify-otp'].includes(route)) {
      await expect(page).not.toHaveURL(/\/login$/)
    }
    const brokenImages = await page.locator('img').evaluateAll((images) => images
      .filter((image) => image.complete && image.naturalWidth === 0)
      .map((image) => image.getAttribute('src')))
    expect(brokenImages, `broken images on ${route}`).toEqual([])
  }
})
