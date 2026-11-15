import { afterEach, expect, it, vi } from 'vitest'

afterEach(() => {
  delete process.env.VAAKMITRA_DEV_API_TARGET
  vi.resetModules()
})

it('dec008 isolates lab probes against the selected local backend target', async () => {
  process.env.VAAKMITRA_DEV_API_TARGET = 'http://127.0.0.1:8001'
  vi.resetModules()
  const { default: config } = await import('./vite.config.js')

  expect(config.server.proxy['/api'].target).toBe('http://127.0.0.1:8001')
  expect(config.server.proxy['/health'].target).toBe('http://127.0.0.1:8001')
  expect(config.server.proxy['/ws'].target).toBe('ws://127.0.0.1:8001')
}, 30_000)
