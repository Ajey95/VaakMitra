import { expect, test } from '@playwright/test'

const USER = {
  id: 'character-test-child',
  email: 'character-test@example.invalid',
  full_name: 'Character Test Parent',
  child_name: 'Maya',
  child_age: 7,
  role: 'user',
  total_stars: 12,
}

async function mockPrivateApi(page) {
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/me') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(USER) })
    }
    if (path.startsWith('/api/story-voice/')) {
      return route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"story_voice_unavailable"}' })
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })
}

async function installSpeechMock(page) {
  await page.addInitScript(() => {
    window.__characterSpeech = []
    class MockUtterance {
      constructor(text) { this.text = text }
    }
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: MockUtterance })
    Object.defineProperty(window, 'speechSynthesis', {
      configurable: true,
      value: {
        cancel() {},
        getVoices: () => [
          { name: 'Test Tamil Voice', lang: 'ta-IN', default: false, localService: true },
          { name: 'Microsoft Ravi', lang: 'en-IN', default: true, localService: true },
          { name: 'Microsoft Heera', lang: 'en-IN', default: false, localService: true },
        ],
        speak(utterance) {
          window.__characterSpeech.push({
            text: utterance.text,
            pitch: utterance.pitch,
            rate: utterance.rate,
            volume: utterance.volume,
            lang: utterance.lang,
            voiceName: utterance.voice?.name,
          })
          utterance.onstart?.()
          window.setTimeout(() => utterance.onend?.(), 20)
        },
      },
    })
  })
}

async function installMicrophoneMock(page) {
  await page.addInitScript(() => {
    window.__kittenPlaybackRates = []
    window.__mockMicLevel = 0
    window.__mediaRecorderStarts = 0
    window.__mediaRecorderStops = 0
    const stream = { getTracks: () => [{ stop() {} }] }
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: async () => stream },
    })
    class MockMediaRecorder {
      constructor() { this.state = 'inactive' }
      start() { this.state = 'recording'; window.__mediaRecorderStarts += 1 }
      stop() {
        this.state = 'inactive'
        window.__mediaRecorderStops += 1
        this.ondataavailable?.({ data: new Blob(['local-child-voice'], { type: 'audio/webm' }) })
        this.onstop?.()
      }
    }
    class MockAudioContext {
      constructor() { this.destination = {} }
      createMediaStreamSource() { return { connect() {} } }
      createAnalyser() {
        return {
          fftSize: 256,
          frequencyBinCount: 128,
          smoothingTimeConstant: 0,
          connect() {},
          disconnect() {},
          getByteFrequencyData(array) { array.fill(Math.round(window.__mockMicLevel * 255)) },
          getByteTimeDomainData(array) { array.fill(145) },
        }
      }
      createBufferSource() {
        const source = {
          playbackRate: { value: 1 }, connect() {}, disconnect() {}, stop() {},
          start() {
            window.__kittenPlaybackRates.push(source.playbackRate.value)
            window.setTimeout(() => source.onended?.(), 15)
          },
        }
        return source
      }
      createBiquadFilter() { return { type: 'lowpass', frequency: { value: 0 }, gain: { value: 0 }, connect() {}, disconnect() {} } }
      createDynamicsCompressor() { return { connect() {}, disconnect() {} } }
      createGain() { return { gain: { value: 1 }, connect() {}, disconnect() {} } }
      decodeAudioData() {
        return Promise.resolve({
          duration: .2,
          numberOfChannels: 1,
          sampleRate: 16000,
          length: 3200,
          getChannelData() { return new Float32Array(3200).fill(.2) },
        })
      }
      createOscillator() { return { frequency: { setValueAtTime() {} }, connect() {}, start() {}, stop() {}, type: 'sine' } }
      close() { return Promise.resolve() }
    }
    Object.defineProperty(window, 'MediaRecorder', { configurable: true, value: MockMediaRecorder })
    Object.defineProperty(window, 'AudioContext', { configurable: true, value: MockAudioContext })
  })
}

test.beforeEach(async ({ page }) => {
  await mockPrivateApi(page)
  await installSpeechMock(page)
  await installMicrophoneMock(page)
})

test('Pippin automatically repeats the child with coordinated kitten expressions', async ({ page }) => {
  const privateRequests = []
  page.on('request', (request) => {
    if (/evaluate|upload/i.test(request.url())) privateRequests.push(request.url())
  })
  await page.goto('/play/pippin')
  const svg = page.getByTestId('pippin-story-svg')
  await expect(page.getByText('Play & Practice / விளையாடிப் பழகலாம்')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Calm / அமைதி' })).toBeVisible()
  await page.getByRole('button', { name: 'Comfort settings / வசதி அமைப்புகள்' }).click()
  await expect(page.getByRole('heading', { name: 'Make practice feel comfortable / விளையாட்டை வசதியாக மாற்றலாம்' })).toBeVisible()
  await page.getByRole('button', { name: 'Save choices / தேர்வுகளைச் சேமிக்கவும்' }).click()
  await expect(svg).toBeVisible()
  await expect(page.getByTestId('pippin-storybook').locator('canvas')).toHaveCount(0)
  await expect(svg.getByTestId('pippin-eyes')).toHaveAttribute('data-state', 'gentle')
  await expect(svg.getByTestId('pippin-mouth')).toHaveAttribute('data-state', 'smile')
  await expect(svg.getByTestId('pippin-tail')).toHaveAttribute('data-state', 'gentle')
  await expect(svg.getByTestId('pippin-ears')).toHaveAttribute('data-state', 'relaxed')
  await expect(svg.getByTestId('pippin-body')).toHaveAttribute('data-state', 'breathing')
  await expect(svg.getByTestId('pippin-paws')).toHaveAttribute('data-state', 'still')

  const permission = page.getByRole('button', { name: 'Enable microphone / மைக்ரோஃபோனை இயக்கவும்' })
  await expect(permission).toBeVisible()
  await expect(page.getByRole('button', { name: /^(Start|Stop|பேசலாம்|முடித்தேன்)$/i })).toHaveCount(0)
  await permission.click()
  await expect(page.getByRole('heading', { name: 'Listening / கேட்கிறேன்' })).toBeVisible()
  await expect(permission).toHaveCount(0)
  await expect(svg.getByTestId('pippin-ears')).toHaveAttribute('data-state', 'forward')
  await expect(svg.getByTestId('pippin-tail')).toHaveAttribute('data-state', 'slow')
  await expect(svg.getByTestId('pippin-body')).toHaveAttribute('data-state', 'listening')

  await page.evaluate(() => { window.__mockMicLevel = 0.35 })
  await page.waitForTimeout(250)
  await page.evaluate(() => { window.__mockMicLevel = 0 })
  await expect.poll(() => page.evaluate(() => window.__mediaRecorderStops), { timeout: 6000 }).toBe(1)
  await expect.poll(() => page.evaluate(() => window.__kittenPlaybackRates), { timeout: 3000 }).toEqual([1.24])
  await expect.poll(() => page.evaluate(() => window.__mediaRecorderStarts), { timeout: 3000 }).toBe(2)
  await expect(page.getByRole('heading', { name: 'Listening / கேட்கிறேன்' })).toBeVisible()

  await page.getByRole('button', { name: 'Dance / ஆடு' }).click()
  await expect(svg).toHaveAttribute('data-mood', 'dance')
  await expect(svg.getByTestId('pippin-mouth')).toHaveAttribute('data-state', 'wide-smile')
  await expect(svg.getByTestId('pippin-tail')).toHaveAttribute('data-state', 'fast')
  await expect(svg.getByTestId('pippin-paws')).toHaveAttribute('data-state', 'dance')
  await page.getByRole('button', { name: 'Sing / பாடு' }).click()
  await expect(svg).toHaveAttribute('data-mood', 'sing')
  await expect(svg.getByTestId('pippin-mouth')).toHaveAttribute('data-state', 'speaking')
  await expect(svg.getByTestId('pippin-ears')).toHaveAttribute('data-state', 'perked')
  expect(privateRequests).toEqual([])
  const saved = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))
  expect(saved).not.toMatch(/audio|blob|transcript|utterance|local-child-voice/i)
})

test('Pippin offers bilingual fixed phrases when the microphone is unavailable', async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: { getUserMedia: async () => { throw new Error('denied') } } })
  })
  await page.goto('/play/pippin')
  const permission = page.getByRole('button', { name: 'Enable microphone / மைக்ரோஃபோனை இயக்கவும்' })
  await permission.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Microphone unavailable. Choose a phrase / மைக்ரோஃபோன் கிடைக்கவில்லை. ஒரு சொல்லைத் தேர்ந்தெடுக்கலாம்.' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Hello / வணக்கம்' })).toBeVisible()
  await page.getByRole('button', { name: 'Hello / வணக்கம்' }).click()
  await expect.poll(() => page.evaluate(() => window.__characterSpeech.at(-1)?.text)).toBe('Hello. வணக்கம்')
})

test('Pippin never overlaps microphone permission requests during an activity', async ({ page }) => {
  await page.goto('/play/pippin')
  await page.evaluate(() => {
    window.__microphoneRequestCount = 0
    navigator.mediaDevices.getUserMedia = () => {
      window.__microphoneRequestCount += 1
      return new Promise((resolve) => {
        window.setTimeout(() => resolve({ getTracks: () => [{ stop() {} }] }), 3500)
      })
    }
  })

  await page.getByRole('button', { name: 'Enable microphone / மைக்ரோஃபோனை இயக்கவும்' }).click()
  await page.getByRole('button', { name: 'Dance / ஆடு' }).click()
  await page.waitForTimeout(2800)

  expect(await page.evaluate(() => window.__microphoneRequestCount)).toBe(1)
})

test('Kavi is a five-page Tamil storybook made from safe raster pictures', async ({ page }) => {
  await page.goto('/play/quest/river-rescue')
  const story = page.getByTestId('kavi-storybook')
  const picture = page.getByTestId('kavi-story-picture')
  await expect(story).toBeVisible()
  await expect(picture).toBeVisible()
  await expect(picture).toHaveAttribute('src', '/assets/storybook/kavi/level-1.png')
  await expect(picture).toHaveAttribute('alt', /கவி/)
  await expect(story.locator('svg[data-testid="kavi-story-svg"]')).toHaveCount(0)
  await expect(story.locator('canvas')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'கவியின் பாலப் பயணம்' })).toBeVisible()
  await expect(page.getByText('விளையாடிப் பழகலாம்')).toBeVisible()
  await expect(page.getByRole('button', { name: 'அமைதி' })).toBeVisible()
  await expect(page.getByText('PLAY & PRACTICE')).toHaveCount(0)
  await expect(page.getByTestId('kavi-progress').locator('li')).toHaveCount(5)
  await expect(page.getByTestId('kavi-picture-scene')).toHaveAttribute('data-page', '1')

  const layout = await story.evaluate((root) => {
    const scene = root.querySelector('.storybook-scene').getBoundingClientRect()
    const card = root.querySelector('.storybook-card').getBoundingClientRect()
    const overlapWidth = Math.max(0, Math.min(scene.right, card.right) - Math.max(scene.left, card.left))
    const overlapHeight = Math.max(0, Math.min(scene.bottom, card.bottom) - Math.max(scene.top, card.top))
    return { overlapArea: overlapWidth * overlapHeight }
  })
  expect(layout.overlapArea).toBe(0)

  await page.getByRole('button', { name: 'கதையைத் தொடங்கலாம்' }).click()
  await expect.poll(() => page.evaluate(() => window.__characterSpeech.at(-1))).toMatchObject({
    lang: 'ta-IN',
  })
  await expect(page.getByLabel('சொல்ல வேண்டியது: அ')).toBeVisible()
  await expect(page.getByTestId('kavi-picture-scene')).toHaveAttribute('data-mood', /speaking|ready/)
})

test('Kavi River Rescue remains playable when all narration services are unavailable', async ({ page }) => {
  await page.goto('/play/quest/river-rescue')
  await page.evaluate(() => {
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: undefined })
    Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: undefined })
  })

  await page.getByRole('button', { name: 'கதையைத் தொடங்கலாம்' }).click()

  await expect(page.getByRole('button', { name: 'சொல்லத் தொடங்கலாம்' })).toBeVisible()
  await expect(page.getByLabel('சொல்ல வேண்டியது: அ')).toBeVisible()
})

test('dec016 ng001 letter lesson stays visual without a phoneme score', async ({ page }) => {
  let legacyScoringCalls = 0
  await page.route('**/api/therapy/lessons/3', (route) => route.fulfill({
    json: { id: 3, type: 'letter', symbol: 'ல', english: 'LA', phoneme: 'la', difficulty: 2 },
  }))
  await page.route('**/api/evaluate/speech', (route) => {
    legacyScoringCalls += 1
    return route.fulfill({ status: 500 })
  })
  await page.goto('/therapy/3')
  await expect(page.getByText(/Visual letter lesson/)).toBeVisible()
  await expect(page.getByText('LA', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('This letter is not word-scored.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start recording' })).toHaveCount(0)
  expect(legacyScoringCalls).toBe(0)
})

test('ng001 Kavi completes five pages with guided support and no unsupported scoring', async ({ page }) => {
  let evaluationCount = 0
  let reportBody = null
  await page.route('**/api/evaluate/tamil-story', async (route) => {
    evaluationCount += 1
    const supported = evaluationCount <= 3
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(supported
        ? { accuracy: 48, matched: false, method: 'acoustic_vowel', transcript: '', feedback_key: 'try_together', capability: 'available', target_id: 'a' }
        : { accuracy: 94, matched: true, method: 'tamil_asr', transcript: 'mock-only', feedback_key: 'wonderful', capability: 'available' }),
    })
  })
  await page.route('**/api/interactive-sessions', async (route) => {
    if (route.request().method() === 'POST') reportBody = route.request().postDataJSON()
    return route.fulfill({ status: 201, contentType: 'application/json', body: '{"status":"recorded"}' })
  })

  await page.goto('/play/quest/river-rescue')
  await page.getByRole('button', { name: 'கதையைத் தொடங்கலாம்' }).click()
  await expect(page.getByRole('button', { name: 'சொல்லத் தொடங்கலாம்' })).toBeVisible()

  await page.getByRole('button', { name: 'சொல்லத் தொடங்கலாம்' }).click()
  await page.getByRole('button', { name: 'முடித்தேன்' }).click()
  await expect(page.getByRole('button', { name: 'கவியுடன் சேர்ந்து சொல்லலாம்' })).toBeVisible()
  await page.getByRole('button', { name: 'கவியுடன் சேர்ந்து சொல்லலாம்' }).click()
  await page.getByRole('button', { name: 'கவியுடன் நடக்கலாம்' }).click()

  for (let pageIndex = 1; pageIndex < 5; pageIndex += 1) {
    await expect(page.getByRole('button', { name: 'சொல்லத் தொடங்கலாம்' })).toBeVisible({ timeout: 10_000 })
    await expect(page.getByTestId('kavi-story-picture')).toHaveAttribute('src', `/assets/storybook/kavi/level-${pageIndex + 1}.png`)
    await page.getByRole('button', { name: 'சொல்லத் தொடங்கலாம்' }).click()
    await page.getByRole('button', { name: 'முடித்தேன்' }).click()
    await expect(page.getByRole('button', { name: 'கவியுடன் சேர்ந்து சொல்லலாம்' })).toBeVisible()
    await page.getByRole('button', { name: 'கவியுடன் சேர்ந்து சொல்லலாம்' }).click()
    await expect(page.getByRole('button', { name: 'கவியுடன் நடக்கலாம்' })).toBeVisible()
    await page.getByRole('button', { name: 'கவியுடன் நடக்கலாம்' }).click()
  }

  await expect(page.getByRole('button', { name: 'கதையை மீண்டும் விளையாடலாம்' })).toBeVisible({ timeout: 10_000 })
  await expect.poll(() => reportBody).not.toBeNull()
  expect(reportBody).toMatchObject({
    activity_id: 'kavi-tamil-story',
    activity_type: 'quest',
    communication_turns: 5,
    successful_turns: 5,
    assistance_counts: { independent: 0, modelled: 5 },
  })
  expect(evaluationCount).toBe(0)
  expect(JSON.stringify(reportBody)).not.toMatch(/transcript|audio|blob|utterance|mock-only/i)
  const stored = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))
  expect(stored).not.toMatch(/transcript|audio|blob|utterance|mock-only/i)
})

test('character experiences respect reduced motion and do not overflow on mobile', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.setViewportSize({ width: 390, height: 844 })
  for (const path of ['/play/pippin', '/play/quest/river-rescue']) {
    await page.goto(path)
    await expect(page.locator('html')).toHaveAttribute('data-interaction-motion', 'reduced')
    await expect(page.locator('[data-testid$="-story-svg"], [data-testid="kavi-story-picture"], [data-testid^="character-stage-"]').first()).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  }
})
