import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import Slide3_Evaluation from './Slide3_Evaluation'

const snapshot = { session_id: 'SES-1', status: 'active', word_id: 'TA_00021', target_word: 'அம்மா', exercise_version: 'ta-core-1.0.0', attempt_count: 0 }

describe('UX-003/006 and FUS-001 therapy rendering', () => {
  it('shows a neutral UNSCORABLE result without a numeric grade or success reward', () => {
    const html = renderToStaticMarkup(<Slide3_Evaluation snapshot={snapshot} phase="active" result={{ decision: 'UNSCORABLE', word_match_probability: null, reason_code: 'CALIBRATION_UNAVAILABLE' }} onSubmit={vi.fn()} />)
    expect(html).toContain('அம்மா')
    expect(html).toContain('Your speech was not graded')
    expect(html).not.toContain('Accuracy')
    expect(html).not.toContain('Confetti')
    expect(html).not.toContain('NaN')
  })

  it('removes capture controls when the server session is paused', () => {
    const html = renderToStaticMarkup(<Slide3_Evaluation snapshot={{ ...snapshot, status: 'paused' }} phase="paused" result={null} onSubmit={vi.fn()} />)
    expect(html).not.toContain('aria-label="Start recording"')
    expect(html).toContain('A grown-up can help continue')
    expect(html).toContain('Practice paused')
  })
})
