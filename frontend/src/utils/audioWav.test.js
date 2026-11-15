import { describe, expect, it, vi } from 'vitest'
import { convertAudioBlobToWav, encodeAudioBufferAsWav } from './audioWav'

function fakeAudioBuffer() {
  return {
    numberOfChannels: 1,
    sampleRate: 16000,
    length: 4,
    getChannelData: () => new Float32Array([0, -1, 1, 0.5]),
  }
}

describe('evaluation WAV conversion', () => {
  it('encodes browser audio as a valid 16-bit PCM WAV file', async () => {
    const wav = encodeAudioBufferAsWav(fakeAudioBuffer())
    const view = new DataView(await wav.arrayBuffer())
    const text = (offset, length) => String.fromCharCode(...new Uint8Array(view.buffer, offset, length))

    expect(wav.type).toBe('audio/wav')
    expect(text(0, 4)).toBe('RIFF')
    expect(text(8, 4)).toBe('WAVE')
    expect(view.getUint16(22, true)).toBe(1)
    expect(view.getUint32(24, true)).toBe(16000)
    expect(view.getUint16(34, true)).toBe(16)
    expect(view.getUint32(40, true)).toBe(8)
  })

  it('decodes a MediaRecorder blob and closes the audio context', async () => {
    const close = vi.fn(async () => {})
    const decodeAudioData = vi.fn(async () => fakeAudioBuffer())
    const scope = {
      AudioContext: class AudioContext {
        decodeAudioData = decodeAudioData
        close = close
      },
    }
    const source = new Blob(['webm-opus'], { type: 'audio/webm' })

    const wav = await convertAudioBlobToWav(source, { scope })

    expect(wav.type).toBe('audio/wav')
    expect(decodeAudioData).toHaveBeenCalledOnce()
    expect(close).toHaveBeenCalledOnce()
  })
})
