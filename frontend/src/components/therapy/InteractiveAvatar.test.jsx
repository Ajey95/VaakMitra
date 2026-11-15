import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import InteractiveAvatar from './InteractiveAvatar'

describe('DEC-012/DEC-025 local 2D interactive avatar', () => {
  it('renders an explicit listening state, approximate viseme and priority stop', () => {
    const html = renderToStaticMarkup(<InteractiveAvatar phase="LISTENING" message="Say அம்மா" targetWord="அம்மா"
      speaking audioLevel={0.4} active onStop={vi.fn()} scopeLabel="ADULT DEVELOPMENT ONLY" />)
    expect(html).toContain('aria-label="Interactive avatar coach"')
    expect(html).toContain('data-avatar-phase="LISTENING"')
    expect(html).toContain('data-viseme=')
    expect(html).toContain('Stop live practice')
    expect(html).toContain('ADULT DEVELOPMENT ONLY')
    expect(html).toContain('Say அம்மா')
  })
})
