import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import ExpressiveAvatar from './ExpressiveAvatar'

const requiredParts = [
  'head', 'arm-left', 'hand-left', 'arm-right', 'hand-right',
  'eye-left', 'eye-right', 'brow-left', 'brow-right',
  'mouth-neutral', 'mouth-a', 'mouth-e', 'mouth-o', 'mouth-m',
]

describe('DEC-026/AVT-001 expressive vector rigs', () => {
  it.each(['meera', 'kavin', 'nila', 'pippin'])('%s exposes the complete shared rig', (avatarId) => {
    const html = renderToStaticMarkup(<ExpressiveAvatar avatarId={avatarId} phase="PROMPTING" speaking audioLevel={0.7} />)
    expect(html).toContain(`data-avatar-id="${avatarId}"`)
    expect(html).toContain('data-expression="speaking"')
    expect(html).toContain('data-gesture="explain"')
    for (const part of requiredParts) expect(html).toContain(`data-avatar-part="${part}"`)
    expect(html).not.toContain('<img')
    expect(html).not.toContain('http:')
    expect(html).not.toContain('https:')
  })

  it('marks still motion and retains a readable accessible name', () => {
    const html = renderToStaticMarkup(<ExpressiveAvatar avatarId="meera" phase="PRAISE" motionLevel="still" />)
    expect(html).toContain('data-motion="still"')
    expect(html).toContain('aria-label="Meera, expressive avatar guide"')
  })
})
