import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { AmbientEffects, CelebrationLayer, TamilStatus } from './SceneEffects'

describe('SceneEffects', () => {
  it('keeps decorative effects hidden from assistive technology', () => {
    const html = renderToStaticMarkup(<AmbientEffects variant="meadow" enabled />)
    expect(html).toContain('aria-hidden="true"')
    expect(html).toContain('data-variant="meadow"')
  })

  it('renders the bounded number of configured particles', () => {
    const html = renderToStaticMarkup(<CelebrationLayer variant="stars" state="success" effectProfile={{ particles: 6, travel: false, durationMs: 1800 }} />)
    expect((html.match(/class="scene-particle"/g) || []).length).toBe(6)
    expect(html).toContain('data-travel="false"')
  })

  it('announces Tamil status politely', () => {
    const html = renderToStaticMarkup(<TamilStatus label="சரியாக செய்தாய்!" />)
    expect(html).toContain('aria-live="polite"')
    expect(html).toContain('சரியாக செய்தாய்!')
  })
})
