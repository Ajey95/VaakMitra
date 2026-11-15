import { describe, expect, it } from 'vitest'
import {
  KAVI_STORY_PAGES,
  buildKaviStoryReport,
  createKaviStoryState,
  getKaviPage,
  kaviStoryReducer,
} from './kaviStory'

const tamilPages = [
  ['a', 'அ', 'கவி ஆற்றங்கரையில் நிற்கிறான். பாதையைத் திறக்க “அ” என்று சொல்லலாமா?'],
  ['ii', 'ஈ', 'மின்மினிப் பூச்சிகள் வழி காட்ட வேண்டும். “ஈ” என்று நீளமாகச் சொல்லுங்கள்.'],
  ['amma', 'அம்மா', 'கவி தன் அம்மாவை அழைக்க வேண்டும். “அம்மா” என்று சொல்லுங்கள்.'],
  ['kavi_vaa', 'கவி வா', 'பாலம் அருகே வந்துவிட்டது. “கவி வா” என்று அழையுங்கள்.'],
  ['kavi_bridge', 'கவி பாலத்தைக் கடக்கலாம்', 'கவி பாலத்தைக் கடக்கத் தயாராக இருக்கிறான். “கவி பாலத்தைக் கடக்கலாம்” என்று சொல்லுங்கள்.'],
]

describe('Kavi Tamil story engine', () => {
  it('uses a unique raster picture for every story level', () => {
    const pictures = KAVI_STORY_PAGES.map((page) => page.picture)
    expect(new Set(pictures).size).toBe(5)
    for (const picture of pictures) {
      expect(picture).toMatch(/^\/assets\/storybook\/kavi\/level-[1-5]\.png$/)
    }
  })

  it('defines the exact five Tamil learning pages in order', () => {
    expect(KAVI_STORY_PAGES.map(({ id, target, narration }) => [id, target, narration])).toEqual(tamilPages)
    expect(new Set(KAVI_STORY_PAGES.map((page) => page.scene))).toEqual(
      new Set(['flowers', 'fireflies', 'family', 'bridge', 'crossing']),
    )
  })

  it('moves through narration, listening, and evaluation deterministically', () => {
    let state = createKaviStoryState(100)
    expect(state.phase).toBe('intro')
    state = kaviStoryReducer(state, { type: 'START' })
    expect(state.phase).toBe('narrating')
    state = kaviStoryReducer(state, { type: 'NARRATION_ENDED' })
    expect(state.phase).toBe('ready')
    state = kaviStoryReducer(state, { type: 'LISTEN' })
    expect(state.phase).toBe('listening')
    state = kaviStoryReducer(state, { type: 'EVALUATE' })
    expect(state.phase).toBe('evaluating')
  })

  it('offers a gentle retry and support after three attempts', () => {
    let state = { ...createKaviStoryState(), phase: 'evaluating' }
    state = kaviStoryReducer(state, { type: 'RESULT', result: { matched: false, accuracy: 42, feedback_key: 'try_together' } })
    expect(state).toMatchObject({ phase: 'ready', pageAttempts: 1, feedbackKey: 'try_together' })

    state = { ...state, phase: 'evaluating' }
    state = kaviStoryReducer(state, { type: 'RESULT', result: { matched: false, accuracy: 57, feedback_key: 'almost' } })
    state = { ...state, phase: 'evaluating' }
    state = kaviStoryReducer(state, { type: 'RESULT', result: { matched: false, accuracy: 58, feedback_key: 'almost' } })
    expect(state).toMatchObject({ phase: 'support', pageAttempts: 3 })

    state = kaviStoryReducer(state, { type: 'USE_HELP' })
    expect(state).toMatchObject({ phase: 'success', assistanceCount: 1, successes: 1 })
  })

  it('uses picture support when the Tamil model is unavailable without inventing a result', () => {
    const state = kaviStoryReducer(
      { ...createKaviStoryState(), phase: 'evaluating' },
      { type: 'RESULT', result: { matched: null, accuracy: null, capability: 'model_unavailable' } },
    )

    expect(state).toMatchObject({ phase: 'support', feedbackKey: 'model_unavailable', lastAccuracy: null })
  })

  it('walks Kavi across all pages and completes on the fifth', () => {
    let state = createKaviStoryState()
    for (let index = 0; index < 5; index += 1) {
      state = { ...state, phase: 'evaluating' }
      state = kaviStoryReducer(state, { type: 'RESULT', result: { matched: true, accuracy: 95, feedback_key: 'wonderful' } })
      expect(state.phase).toBe('success')
      state = kaviStoryReducer(state, { type: 'NEXT' })
      expect(state.phase).toBe('walking')
      state = kaviStoryReducer(state, { type: 'WALK_FINISHED' })
    }
    expect(state).toMatchObject({ phase: 'complete', pageIndex: 4, successes: 5 })
  })

  it('returns the active page and resets safely', () => {
    const state = { ...createKaviStoryState(), pageIndex: 2, phase: 'ready' }
    expect(getKaviPage(state).target).toBe('அம்மா')
    expect(kaviStoryReducer(state, { type: 'RESET' })).toEqual(createKaviStoryState())
  })

  it('builds an aggregate-only report with no transcript or audio', () => {
    const report = buildKaviStoryReport({
      state: { ...createKaviStoryState(100), phase: 'complete', successes: 4, totalAttempts: 7, assistanceCount: 1 },
      completedAt: 5100,
    })

    expect(report).toMatchObject({
      activity_id: 'kavi-tamil-story',
      activity_type: 'quest',
      started_at: new Date(100).toISOString(),
      completed_at: new Date(5100).toISOString(),
      communication_turns: 5,
      successful_turns: 4,
      attempts: 7,
      assistance_counts: { independent: 3, verbal_prompt: 0, visual_prompt: 0, modelled: 1, skipped: 0 },
      duration_ms: 5000,
      effort_points: 8,
    })
    expect(JSON.stringify(report)).not.toMatch(/transcript|audio|recording|utterance/i)
  })
})
