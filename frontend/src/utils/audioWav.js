function writeAscii(view, offset, text) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index))
  }
}

export function encodeAudioBufferAsWav(audioBuffer) {
  const channels = Number(audioBuffer?.numberOfChannels)
  const sampleRate = Number(audioBuffer?.sampleRate)
  const frameCount = Number(audioBuffer?.length)
  if (!Number.isInteger(channels) || channels < 1 || !Number.isFinite(sampleRate) || sampleRate < 1 || !Number.isInteger(frameCount) || frameCount < 1) {
    throw new TypeError('A decoded audio buffer is required')
  }

  const bytesPerSample = 2
  const dataSize = frameCount * channels * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)
  writeAscii(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeAscii(view, 8, 'WAVE')
  writeAscii(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, channels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * channels * bytesPerSample, true)
  view.setUint16(32, channels * bytesPerSample, true)
  view.setUint16(34, 16, true)
  writeAscii(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  const channelData = Array.from({ length: channels }, (_, channel) => audioBuffer.getChannelData(channel))
  let offset = 44
  for (let frame = 0; frame < frameCount; frame += 1) {
    for (let channel = 0; channel < channels; channel += 1) {
      const sample = Math.max(-1, Math.min(1, channelData[channel][frame] || 0))
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
      offset += bytesPerSample
    }
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

export async function convertAudioBlobToWav(blob, { scope = globalThis } = {}) {
  if (!(blob instanceof Blob) || blob.size === 0) throw new TypeError('A non-empty recording is required')
  if (blob.type === 'audio/wav' || blob.type === 'audio/x-wav') return blob
  const AudioContextCtor = scope.AudioContext || scope.webkitAudioContext
  if (!AudioContextCtor) throw new Error('Audio conversion is unavailable')
  const context = new AudioContextCtor()
  try {
    const decoded = await context.decodeAudioData(await blob.arrayBuffer())
    return encodeAudioBufferAsWav(decoded)
  } finally {
    await context.close?.()
  }
}
