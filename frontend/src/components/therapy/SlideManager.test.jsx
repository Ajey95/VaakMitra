import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import SlideManager from './SlideManager'

const snapshot = { session_id: 'SES-1', status: 'active', word_id: 'TA_00021', target_word: 'அம்மா', exercise_version: 'ta-core-1.0.0', attempt_count: 0 }
const render = (phase) => renderToStaticMarkup(<MemoryRouter><SlideManager snapshot={{ ...snapshot, status: phase === 'paused' ? 'paused' : 'active' }} phase={phase} onPause={vi.fn()} onStop={vi.fn()} onSubmit={vi.fn()} /></MemoryRouter>)

describe('SES-001/003/007 guarded therapy shell', () => {
  it('keeps the red Break / Stop control visible alongside the server-selected word', () => {
    const html = render('active')
    expect(html).toContain('அம்மா')
    expect(html).toContain('Break or stop')
    expect(html).toContain('bg-red-600')
    expect(html).not.toContain('Go to slide')
    expect(html).not.toContain('Next Lesson')
  })

  it('keeps Break / Stop usable while an assessment is processing', () => {
    const html = render('processing')
    expect(html).toContain('Break or stop')
    expect(html).toContain('bg-red-600')
    expect(html).toContain('aria-label="Interactive avatar coach"')
    expect(html).toContain('data-avatar-phase="PROCESSING"')
  })

  it('does not expose child resume in a paused session', () => {
    const html = render('paused')
    expect(html).toContain('A grown-up can help continue')
    expect(html).toContain('End session')
    expect(html).not.toContain('Resume session')
  })
})
