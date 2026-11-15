import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import BalloonScene from './BalloonScene'

describe('BalloonScene', () => {
  it('renders the requested expression and preserves its accessible meter', () => {
    const html = renderToStaticMarkup(<BalloonScene level={0.9} target={[0.25, 0.7]} active visualState="too-strong" motionLevel="full" />)
    expect(html).toContain('data-visual-state="too-strong"')
    expect(html).toContain('balloon-face')
    expect(html).toContain('Voice level 90 percent')
  })

  it('renders the flight reward only for completion', () => {
    expect(renderToStaticMarkup(<BalloonScene level={0} visualState="complete" motionLevel="full" />)).toContain('balloon-flight-reward')
    expect(renderToStaticMarkup(<BalloonScene level={0} visualState="idle" motionLevel="full" />)).not.toContain('balloon-flight-reward')
  })
})
