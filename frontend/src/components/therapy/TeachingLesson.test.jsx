import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'
import Slide1_Picture from './Slide1_Picture'
import Slide2_Animation from './Slide2_Animation'

const letter = { id: 1, type: 'letter', symbol: 'அ', english: 'A', phoneme: 'a', difficulty: 1, mouth: '', tip: 'Look at the shape.' }

describe('DEC-016/UX-004/007 silent inherited letter teaching', () => {
  it('keeps the picture slide and a Next control without browser Listen/TTS', () => {
    const html = renderToStaticMarkup(<Slide1_Picture lesson={letter} onNext={vi.fn()} silent />)
    expect(html).toContain('அ')
    expect(html).toContain('lesson-built-in-visual')
    expect(html).toContain('Next')
    expect(html).not.toContain('>Listen<')
  })

  it('keeps a second visual teaching step without audio or scoring controls', () => {
    const html = renderToStaticMarkup(<Slide2_Animation lesson={letter} onNext={vi.fn()} onPrev={vi.fn()} silent />)
    expect(html).toContain('அ')
    expect(html).toContain('Finish')
    expect(html).not.toContain('Play Video')
    expect(html).not.toContain('Play Audio')
    expect(html).not.toContain('Evaluate')
  })
})
