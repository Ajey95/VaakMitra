import React from 'react'
import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import AvatarPicker from './AvatarPicker'

describe('AvatarPicker (DEC-026/AVT-001..006)', () => {
  it('offers every governed guide and no remote or upload source', () => {
    const html = renderToStaticMarkup(<AvatarPicker preference={{ avatarId: 'nila', paletteId: 'lotus', motionLevel: 'reduced' }}/>)
    for (const name of ['Meera', 'Kavin', 'Nila', 'Pippin']) expect(html).toContain(name)
    expect(html).toContain('data-selected="true"')
    expect(html).toContain('Preview reactions')
    expect(html).toContain('Use this guide')
    expect(html).not.toContain('type="file"')
    expect(html).not.toMatch(/(?:src|href)="https?:\/\//)
  })

  it('keeps the preview usable as a labelled mobile region', () => {
    const html = renderToStaticMarkup(<AvatarPicker preference={{ avatarId: 'meera', paletteId: 'coral-teal', motionLevel: 'still' }}/>)
    expect(html).toContain('aria-label="Choose a practice guide"')
    expect(html).toContain('aria-label="Preview Meera"')
    expect(html).toContain('data-motion="still"')
  })
})
