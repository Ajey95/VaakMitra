import { describe, expect, it } from 'vitest'
import { resolveApiBaseUrl, resolveCanonicalApiBaseUrl } from './apiConfig'

describe('API base URL resolution', () => {
  it('always uses the Vite proxy in development even when a stale port override exists', () => {
    expect(resolveApiBaseUrl({
      isDevelopment: true,
      configuredUrl: 'http://127.0.0.1:8001/api',
    })).toBe('/api')
  })

  it('keeps an explicit production API URL and otherwise uses the same-origin API', () => {
    expect(resolveApiBaseUrl({ isDevelopment: false, configuredUrl: 'https://api.example.com/api' }))
      .toBe('https://api.example.com/api')
    expect(resolveApiBaseUrl({ isDevelopment: false, configuredUrl: '' })).toBe('/api')
  })

  it('does not double the /api prefix on canonical word-session routes', () => {
    expect(resolveCanonicalApiBaseUrl({ isDevelopment: true, configuredUrl: 'http://127.0.0.1:8001/api' })).toBe('')
    expect(resolveCanonicalApiBaseUrl({ isDevelopment: false, configuredUrl: 'https://api.example.com/api' })).toBe('https://api.example.com')
  })
})
