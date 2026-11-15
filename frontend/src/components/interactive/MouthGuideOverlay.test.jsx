import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import MouthGuideOverlay from './MouthGuideOverlay'

const target = { model: 'open', sound: 'அ', cue: 'வாயைத் திறக்கவும்' }

describe('MouthGuideOverlay', () => {
  it('renders the therapist and semantic feedback state', () => {
    const html = renderToStaticMarkup(<MouthGuideOverlay target={target} visualState="close" progress={0.5} />)
    expect(html).toContain('data-visual-state="close"')
    expect(html).toContain('/assets/interactive/mouth-mirror/mouth-mirror-therapist.png')
    expect(html).toContain('Hold progress 50 percent')
  })

  it('announces matched feedback in Tamil', () => {
    const html = renderToStaticMarkup(<MouthGuideOverlay target={target} visualState="matched" matched progress={1} />)
    expect(html).toContain('சரியாக செய்தாய்!')
    expect(html).toContain('is-matched')
  })
})
