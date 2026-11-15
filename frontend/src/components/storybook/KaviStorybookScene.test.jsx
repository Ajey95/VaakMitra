import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import KaviStorybookScene from './KaviStorybookScene'

describe('KaviStorybookScene', () => {
  it('renders supportive river overlays for the current mood', () => {
    const html = renderToStaticMarkup(<KaviStorybookScene pageIndex={2} mood="encourage" motionLevel="full" picture="/level.png" message="மீண்டும் முயற்சி செய்வோம்" />)
    expect(html).toContain('data-mood="encourage"')
    expect(html).toContain('kavi-river-effects')
    expect(html).toContain('kavi-retry-cue')
  })

  it('renders a completion celebration only for celebrate mood', () => {
    expect(renderToStaticMarkup(<KaviStorybookScene mood="celebrate" picture="/level.png" />)).toContain('kavi-crossing-celebration')
    expect(renderToStaticMarkup(<KaviStorybookScene mood="idle" picture="/level.png" />)).not.toContain('kavi-crossing-celebration')
  })
})
