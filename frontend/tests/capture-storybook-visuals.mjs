import { chromium } from '@playwright/test'

const browser = await chromium.launch({ headless: true })

async function prepare(page) {
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        id: 'visual-child', email: 'visual@example.invalid', full_name: 'Visual Parent',
        child_name: 'Maya', child_age: 7, role: 'user', total_stars: 12,
      }) })
    }
    if (path.startsWith('/api/story-voice/')) {
      return route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"story_voice_unavailable"}' })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
  await page.addInitScript(() => {
    class Utterance { constructor(text) { this.text = text } }
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: Utterance })
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
      cancel() {}, getVoices: () => [{ name: 'Tamil', lang: 'ta-IN' }],
      speak(utterance) { utterance.onstart?.(); setTimeout(() => utterance.onend?.(), 50) },
    } })
  })
}

for (const viewport of [{ name: 'desktop', width: 1440, height: 1000 }, { name: 'mobile', width: 390, height: 844 }]) {
  const page = await browser.newPage({ viewport })
  await prepare(page)
  await page.goto('http://127.0.0.1:5173/play/quest/river-rescue')
  await page.getByRole('button', { name: 'கதையைத் தொடங்கலாம்' }).click()
  await page.getByRole('button', { name: 'சொல்லத் தொடங்கலாம்' }).waitFor()
  await page.screenshot({ path: `../docs/qa/kavi-storybook-${viewport.name}.png`, fullPage: true })
  await page.goto('http://127.0.0.1:5173/play/pippin')
  await page.getByTestId('pippin-story-svg').waitFor()
  await page.screenshot({ path: `../docs/qa/pippin-storybook-${viewport.name}.png`, fullPage: true })
  await page.close()
}

await browser.close()
