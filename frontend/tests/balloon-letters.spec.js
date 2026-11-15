import { expect, test } from '@playwright/test'

test('balloon crosses letter gates and speaks each phoneme once', async ({ page }) => {
  await page.route('**/api/**', async (route) => {
    const pathname = new URL(route.request().url()).pathname
    if (pathname === '/api/auth/me') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ email: 'demo@speakeasy.app', full_name: 'Demo Parent', child_name: 'Kavi', role: 'user' }),
      })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.addInitScript(() => {
    window.__letterSounds = []
    class MockUtterance { constructor(text) { this.text = text } }
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: MockUtterance })
    Object.defineProperty(window, 'speechSynthesis', {
      configurable: true,
      value: {
        getVoices: () => [{ name: 'Veena', lang: 'en-IN', localService: true }],
        speak: (utterance) => window.__letterSounds.push({ text: utterance.text, pitch: utterance.pitch, rate: utterance.rate }),
        cancel() {},
      },
    })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: async () => { throw new Error('demo mode') } },
    })
  })

  await page.goto('/play/arcade/breath-balloon', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: 'Check my microphone' }).click()
  await page.getByRole('button', { name: 'Use screen control' }).click()
  await expect(page.getByTestId('letter-obstacle')).toHaveCount(3)
  await expect(page.getByTestId('letter-obstacle').allTextContents()).resolves.toEqual(['A', 'B', 'M'])

  await page.getByRole('button', { name: 'Start round' }).click()
  const slider = page.getByLabel('Balloon voice level')
  await slider.fill('60')

  await expect.poll(() => page.evaluate(() => window.__letterSounds.filter(({ pitch }) => pitch === 1.75))).toEqual([
    { text: 'ah', pitch: 1.75, rate: 0.68 },
    { text: 'buh', pitch: 1.75, rate: 0.68 },
  ])
  await expect(page.getByText('B says buh')).toBeVisible()
})
