import { expect, test } from '@playwright/test'

const USER = {
  id: 'page-audit-user',
  email: 'page-audit@example.invalid',
  full_name: 'Page Audit Parent',
  child_name: 'Kavi',
  child_age: 7,
  language: 'Tamil',
  role: 'user',
  total_sessions: 12,
  total_stars: 180,
}

const LESSON = {
  id: 3,
  symbol: 'ல',
  english: 'LA',
  phoneme: 'la',
  type: 'letter',
  difficulty: 2,
  image: '/assets/letters/la.png',
}

async function mockPrivateApi(page) {
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(USER) })
    }
    if (path === '/api/therapy/lessons/3') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(LESSON) })
    }
    return route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"audit backend unavailable"}' })
  })
}

test('forgot password enters the reset flow instead of changing the URL hash', async ({ page }) => {
  await page.route('**/api/auth/me', (route) => route.fulfill({
    status: 401,
    contentType: 'application/json',
    body: '{"detail":"Not authenticated"}',
  }))

  await page.goto('/login')
  await page.getByRole('link', { name: 'Forgot password?' }).click()

  await expect(page).toHaveURL(/\/forgot-password$/)
  await expect(page.getByRole('heading', { name: 'Forgot your password?' })).toBeVisible()
})

test('therapy uses built-in visuals and never renders a broken lesson image', async ({ page }) => {
  await mockPrivateApi(page)
  await page.goto('/therapy/3')
  await expect(page.getByText('LA', { exact: true }).first()).toBeVisible()

  const brokenImages = await page.locator('img').evaluateAll((images) => images
    .filter((image) => image.complete && image.naturalWidth === 0)
    .map((image) => image.getAttribute('src')))
  expect(brokenImages).toEqual([])
})

test('training videos expose a real local player', async ({ page }) => {
  await mockPrivateApi(page)
  await page.goto('/videos')

  const player = page.getByTestId('pronunciation-video')
  await expect(player).toBeVisible()
  await expect(player).toHaveAttribute('controls', '')
  await expect(player).toHaveAttribute('src', /pronounciation_a.*\.mp4/)
})

test('letter learning Play Sound invokes local speech synthesis', async ({ page }) => {
  await page.addInitScript(() => {
    window.__spokenLetters = []
    class MockUtterance { constructor(text) { this.text = text } }
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: MockUtterance })
    Object.defineProperty(window, 'speechSynthesis', {
      configurable: true,
      value: {
        cancel() {},
        getVoices: () => [{ name: 'Tamil Test Voice', lang: 'ta-IN', localService: true }],
        speak(utterance) {
          window.__spokenLetters.push({ text: utterance.text, lang: utterance.lang })
          utterance.onstart?.()
          utterance.onend?.()
        },
      },
    })
  })
  await mockPrivateApi(page)
  await page.goto('/letter-learning')
  await page.getByRole('button', { name: 'Play Sound' }).click()

  await expect.poll(() => page.evaluate(() => window.__spokenLetters)).toEqual([
    { text: 'அ', lang: 'ta-IN' },
  ])
})

test('Game Hub Play opens a real playable destination', async ({ page }) => {
  await mockPrivateApi(page)
  await page.goto('/games')
  await page.getByRole('button', { name: 'Play Alphabet Match' }).click()

  await expect(page).toHaveURL(/\/games#alphabet-match$/)
  await expect(page.getByTestId('alphabet-match-game')).toBeFocused()
})

test('Settings help cards navigate to working support pages', async ({ page }) => {
  await mockPrivateApi(page)
  await page.goto('/settings')
  await page.getByRole('button', { name: /How to Use SpeakEasy/ }).click()

  await expect(page).toHaveURL(/\/help$/)
  await expect(page.getByRole('heading', { name: 'Help & Support' })).toBeVisible()
})

test('Help quick actions and articles reveal real content', async ({ page }) => {
  await mockPrivateApi(page)
  await page.goto('/help')
  await page.getByRole('button', { name: /Video Tutorials/ }).click()
  await expect(page).toHaveURL(/\/videos$/)

  await page.goto('/help')
  const article = page.getByRole('button', { name: /Setting up camera & microphone permissions/ })
  await article.click()
  await expect(article).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByText(/open the lock icon beside the address/)).toBeVisible()
})

test('Tongue Tracking requests a real private camera stream and releases it', async ({ page }) => {
  await page.addInitScript(() => {
    window.__cameraRequests = 0
    window.__cameraStops = 0
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async () => {
          window.__cameraRequests += 1
          return { getTracks: () => [{ stop: () => { window.__cameraStops += 1 } }] }
        },
      },
    })
    Object.defineProperty(HTMLMediaElement.prototype, 'srcObject', { configurable: true, writable: true, value: null })
    HTMLMediaElement.prototype.play = async () => {}
  })
  await mockPrivateApi(page)
  await page.goto('/tongue-tracking')
  await page.getByRole('button', { name: 'Start Camera' }).click()

  await expect(page.getByTestId('tongue-camera')).toBeVisible()
  await expect.poll(() => page.evaluate(() => window.__cameraRequests)).toBe(1)
  await page.getByRole('button', { name: 'Stop' }).click()
  await expect.poll(() => page.evaluate(() => window.__cameraStops)).toBe(1)
})

test('Reports Save as PDF opens the browser print dialog', async ({ page }) => {
  await page.addInitScript(() => {
    window.__printCalls = 0
    window.print = () => { window.__printCalls += 1 }
  })
  await mockPrivateApi(page)
  await page.goto('/reports')
  await page.getByRole('button', { name: /Download PDF|Save as PDF/ }).click()

  await expect.poll(() => page.evaluate(() => window.__printCalls)).toBe(1)
})

test('Profile avatar and security controls perform real actions', async ({ page }) => {
  await mockPrivateApi(page)
  await page.goto('/profile')
  await page.locator('input[type="file"][accept="image/*"]').setInputFiles({
    name: 'avatar.png',
    mimeType: 'image/png',
    buffer: Buffer.from('small-avatar'),
  })
  await expect(page.getByTestId('profile-avatar-preview')).toBeVisible()

  await page.getByRole('button', { name: 'Change Password' }).click()
  await expect(page).toHaveURL(/\/settings$/)
})

test('Profile edits are sent to the profile API', async ({ page }) => {
  let update
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(USER) })
    }
    if (path === '/api/profile/personal') {
      update = route.request().postDataJSON()
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(update) })
    }
    return route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"audit backend unavailable"}' })
  })

  await page.goto('/profile')
  await page.getByRole('button', { name: 'Edit Profile' }).click()
  await page.getByLabel('Full Name').fill('Updated Parent')
  await page.getByRole('button', { name: 'Save' }).click()

  await expect.poll(() => update).toMatchObject({ full_name: 'Updated Parent' })
})

test('gov007 appointments fail closed when the backend is unavailable', async ({ page }) => {
  await mockPrivateApi(page)
  await page.goto('/appointments')
  await expect(page.getByText('audit backend unavailable')).toBeVisible()
  await expect(page.getByTitle('Reschedule')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()
})

test('DEC-026 parent chooses a local expressive guide that survives reload on mobile', async ({ page }) => {
  await mockPrivateApi(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/profile')
  await page.getByRole('button', { name: 'Preferences' }).click()

  const picker = page.getByRole('region', { name: 'Choose a practice guide' })
  await expect(picker).toBeVisible()
  await picker.getByRole('button', { name: /Nila/ }).click()
  await picker.getByRole('button', { name: 'Lotus' }).click()
  await picker.getByRole('button', { name: /Still/ }).click()
  await picker.getByRole('button', { name: 'Celebrate' }).click()
  await expect(picker.getByRole('img', { name: 'Nila, expressive avatar guide' }).first()).toHaveAttribute('data-avatar-phase', 'PRAISE')
  await picker.getByRole('button', { name: 'Use this guide' }).click()

  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('vaakmitra:avatar:v1:child:page-audit-user')))).toEqual({
    schemaVersion: 1, avatarId: 'nila', paletteId: 'lotus', motionLevel: 'still',
  })
  await page.reload()
  await page.getByRole('button', { name: 'Preferences' }).click()
  await expect(page.getByRole('region', { name: 'Choose a practice guide' }).getByRole('img', { name: 'Nila, expressive avatar guide' }).first()).toHaveAttribute('data-motion', 'still')
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
})

test('gov007 parent dashboard never invents invoices or progress on API failure', async ({ page }) => {
  await mockPrivateApi(page)
  await page.goto('/parent')
  await expect(page.getByText('Practice summary is unavailable')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Download Invoices' })).toHaveCount(0)
})

test('public and registration pages contain no dead hash links', async ({ page }) => {
  await page.route('**/api/auth/me', (route) => route.fulfill({
    status: 401,
    contentType: 'application/json',
    body: '{"detail":"Not authenticated"}',
  }))
  await page.goto('/')
  await expect(page.locator('footer')).toBeVisible()
  await expect(page.locator('a[href="#"]')).toHaveCount(0)

  await page.goto('/register')
  await page.getByLabel('Parent / Guardian Name').fill('Test Parent')
  await page.getByLabel("Child's Name").fill('Maya')
  await page.getByLabel("Child's Age").fill('7')
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.getByRole('link', { name: 'Terms of Service' })).toHaveAttribute('href', '/about#terms')
  await expect(page.getByRole('link', { name: 'Privacy Policy' })).toHaveAttribute('href', '/about#privacy')
})

test('password reset calls the API through request, OTP, and new password', async ({ page }) => {
  const calls = []
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') {
      return route.fulfill({ status: 401, contentType: 'application/json', body: '{"detail":"Not authenticated"}' })
    }
    calls.push({ path, body: route.request().postDataJSON() })
    if (path === '/api/auth/verify-otp') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: '{"valid":true}' })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{"message":"ok"}' })
  })

  await page.goto('/forgot-password')
  await page.getByLabel('Email Address').fill('parent@example.com')
  await page.getByRole('button', { name: 'Send Reset Code' }).click()
  await expect.poll(() => calls[0]).toEqual({
    path: '/api/auth/forgot-password',
    body: { email: 'parent@example.com' },
  })
  await page.getByRole('button', { name: 'Enter Reset Code' }).click()

  const otpInputs = page.locator('input[inputmode="numeric"]')
  for (let index = 0; index < 6; index += 1) await otpInputs.nth(index).fill(String(index + 1))
  await page.getByRole('button', { name: 'Verify Code' }).click()
  await expect(page.getByLabel('New Password', { exact: true })).toBeVisible()
  await page.getByLabel('New Password', { exact: true }).fill('NewSafePassword1!')
  await page.getByLabel('Confirm New Password').fill('NewSafePassword1!')
  await page.getByRole('button', { name: 'Reset Password' }).click()

  await expect(page).toHaveURL(/\/login$/)
  expect(calls).toEqual([
    { path: '/api/auth/forgot-password', body: { email: 'parent@example.com' } },
    { path: '/api/auth/verify-otp', body: { email: 'parent@example.com', otp: '123456' } },
    { path: '/api/auth/reset-password', body: { email: 'parent@example.com', otp: '123456', new_password: 'NewSafePassword1!' } },
  ])
})
