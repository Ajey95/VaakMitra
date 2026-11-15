import { useEffect, useRef, useState } from 'react'
import { encodeAudioBufferAsWav } from '../../utils/audioWav'
import InteractiveAvatar from '../../components/therapy/InteractiveAvatar'
import { createLiveAvatarFlow } from '../avatar/liveAvatarFlow'
import { createSpeechEndDetector } from '../avatar/speechEndDetector'
import AdultChunkCoach from './AdultChunkCoach'
import { createChunkCoachFlow } from './chunkCoachFlow'
import { useAvatarPreference } from '../avatar/useAvatarPreference'

async function labRequest(path, options = {}) {
  const response = await fetch(`/api/dev/word-lab/${path}`, { credentials: 'include', ...options })
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new Error(typeof body?.detail === 'string' ? body.detail : `HTTP ${response.status}`)
  return body
}

function avatarMessage(phase, targetWord) {
  const messages = {
    IDLE: 'Press Start live practice when you are ready.',
    PROMPTING: 'Listen to the whole word first.',
    LISTENING: 'Now you say the whole word. I will stop listening after you finish.',
    PROCESSING: 'I am checking this adult engineering attempt locally.',
    PRAISE: 'மிக நன்று! The whole-word development match completed.',
    COACH: 'Listen to the selected written part, then hear the complete word.',
    RETRY: 'Now try the complete word again.',
    BREAK: 'Two coaching cycles are complete. Take a break before resetting.',
    ERROR: 'I could not use that recording. Start again for a fresh capture.',
  }
  return targetWord ? `${messages[phase] ?? messages.ERROR}` : 'Choose an engineering word first.'
}

export default function DiagnosticPanel() {
  const avatarPreference = useAvatarPreference('')
  const [consent, setConsent] = useState(false)
  const [opened, setOpened] = useState(false)
  const [runtime, setRuntime] = useState(null)
  const [word, setWord] = useState('')
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [checks, setChecks] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [recording, setRecording] = useState(false)
  const coachFlow = useRef(null)
  if (!coachFlow.current) coachFlow.current = createChunkCoachFlow()
  const [coach, setCoach] = useState(coachFlow.current.state)
  const [localVoice, setLocalVoice] = useState(null)
  const [speaking, setSpeaking] = useState(false)
  const liveFlow = useRef(null)
  if (!liveFlow.current) liveFlow.current = createLiveAvatarFlow()
  const [liveAvatar, setLiveAvatar] = useState(liveFlow.current.state)
  const [avatarAudioLevel, setAvatarAudioLevel] = useState(0)
  const pending = useRef(null)
  const picker = useRef(null)
  const micButton = useRef(null)
  const capture = useRef(null)
  const captureGeneration = useRef(0)
  const speechTask = useRef(null)
  const localVoiceRef = useRef(null)
  const coachingBlocksAudio = ['focus', 'blend', 'break'].includes(coach.phase)
  const selectedTarget = runtime?.words?.find((item) => item.word_id === word)?.target_word ?? ''

  useEffect(() => {
    const synthesis = window.speechSynthesis
    if (!synthesis) return undefined
    const refresh = () => {
      const voice = synthesis.getVoices().find((item) =>
        item.localService === true && item.lang?.toLowerCase().startsWith('ta')) ?? null
      localVoiceRef.current = voice
      setLocalVoice(voice)
    }
    refresh()
    synthesis.addEventListener?.('voiceschanged', refresh)
    return () => synthesis.removeEventListener?.('voiceschanged', refresh)
  }, [])

  function cancelSpeech() {
    speechTask.current?.finish(false)
    speechTask.current = null
    window.speechSynthesis?.cancel()
    setSpeaking(false)
  }

  function speakExample(text) {
    if (!localVoice || recording || busy || !window.speechSynthesis || !window.SpeechSynthesisUtterance) return
    cancelSpeech()
    const utterance = new window.SpeechSynthesisUtterance(text)
    utterance.voice = localVoice
    utterance.lang = localVoice.lang
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)
    setSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }

  function speakLivePrompt(text, turn, { allowInactive = false } = {}) {
    cancelSpeech()
    const isCurrentTurn = () => liveFlow.current.state.turn === turn && (liveFlow.current.state.active || allowInactive)
    if (!isCurrentTurn()) return Promise.resolve(false)
    return new Promise((resolve) => {
      let settled = false
      let timer = null
      const finish = (completed) => {
        if (settled) return
        settled = true
        if (timer) window.clearTimeout(timer)
        if (speechTask.current?.finish === finish) speechTask.current = null
        setSpeaking(false)
        resolve(completed && isCurrentTurn())
      }
      const voice = localVoiceRef.current
      if (voice && window.speechSynthesis && window.SpeechSynthesisUtterance) {
        const utterance = new window.SpeechSynthesisUtterance(text)
        utterance.voice = voice
        utterance.lang = voice.lang
        utterance.onstart = () => setSpeaking(true)
        utterance.onend = () => finish(true)
        utterance.onerror = () => finish(true)
        speechTask.current = { finish }
        setSpeaking(true)
        window.speechSynthesis.speak(utterance)
      } else {
        setSpeaking(true)
        timer = window.setTimeout(() => finish(true), Math.min(1400, 500 + String(text).length * 90))
        speechTask.current = { finish, timer }
      }
    })
  }

  useEffect(() => () => {
    captureGeneration.current += 1
    pending.current?.abort()
    liveFlow.current.stop()
    speechTask.current?.finish(false)
    if (speechTask.current?.timer) window.clearTimeout(speechTask.current.timer)
    speechTask.current = null
    window.speechSynthesis?.cancel()
    const active = capture.current
    if (active) {
      window.clearTimeout(active.timer)
      active.processor.disconnect()
      active.source.disconnect()
      active.stream.getTracks().forEach((track) => track.stop())
      active.context.close().catch(() => {})
      capture.current = null
    }
  }, [])

  async function status() {
    const value = await labRequest('status', { signal: AbortSignal.timeout(8000) })
    setRuntime(value)
    setWord((previous) => value.words?.some((item) => item.word_id === previous) ? previous : value.words?.[0]?.word_id ?? '')
  }

  async function action(callback) {
    setBusy(true)
    setError('')
    try { return await callback() } catch (failure) { if (failure.name !== 'AbortError') setError(failure.message); return undefined } finally { setBusy(false) }
  }

  async function open() {
    await labRequest('open', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ adult_test_only: true }), signal: AbortSignal.timeout(8000) })
    setOpened(true)
    await status()
  }

  async function submitAudio(audio) {
    const controller = new AbortController()
    pending.current = controller
    const form = new FormData()
    form.append('audio', audio, 'adult-attempt.wav')
    form.append('word_id', word)
    setResult(null)
    try {
      const value = await labRequest('assess', { method: 'POST', body: form,
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(65000)]) })
      let nextCoach = coachFlow.current.state
      if (!controller.signal.aborted) {
        setResult(value)
        nextCoach = coachFlow.current.start(value.chunk_coach, value.development_result?.decision)
        setCoach(nextCoach)
      }
      await status()
      return controller.signal.aborted ? null : { value, nextCoach }
    } finally {
      if (pending.current === controller) pending.current = null
    }
  }

  async function assess() {
    if (!file || !word || !opened) return
    if (!file.name.toLowerCase().endsWith('.wav') || file.size === 0 || file.size > 8 * 1024 * 1024 - 4096) {
      setError('Choose a non-empty WAV smaller than 8 MiB.'); return
    }
    await action(() => submitAudio(file))
  }

  async function startMicrophone(options = {}) {
    const automatic = options?.automatic === true
    const turn = options?.turn
    if (!opened || !word || !runtime?.pipeline_ready || busy || recording || (coachingBlocksAudio && !automatic)) return
    // UX-002/DCH-004: cancel example speech before requesting a microphone track.
    cancelSpeech()
    setError('')
    setResult(null)
    setFile(null)
    if (picker.current) picker.current.value = ''
    const generation = ++captureGeneration.current
    try {
      const AudioContextCtor = window.AudioContext || window.webkitAudioContext
      if (!navigator.mediaDevices?.getUserMedia || !AudioContextCtor) throw new Error('Microphone recording is unavailable in this browser')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      if (generation !== captureGeneration.current) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }
      let context = null
      try {
        context = new AudioContextCtor()
        const source = context.createMediaStreamSource(stream)
        const processor = context.createScriptProcessor(4096, 1, 1)
        const active = { context, source, processor, stream, chunks: [], frames: 0, startedAt: Date.now(), timer: null,
          automatic, turn, detector: automatic ? createSpeechEndDetector({ sampleRate: context.sampleRate }) : null, stopping: false }
        processor.onaudioprocess = (event) => {
          const samples = event.inputBuffer.getChannelData(0)
          if (active.frames + samples.length <= context.sampleRate * 8) {
            active.chunks.push(samples.slice())
            active.frames += samples.length
          }
          if (active.detector) {
            const speech = active.detector.push(samples)
            setAvatarAudioLevel(Math.min(1, speech.level * 4))
            if (speech.shouldStop && !active.stopping) {
              active.stopping = true
              Promise.resolve().then(() => stopAndTest({ automatic: true, turn }))
            }
          }
        }
        source.connect(processor)
        processor.connect(context.destination)
        await context.resume()
        if (generation !== captureGeneration.current) {
          processor.disconnect()
          source.disconnect()
          stream.getTracks().forEach((track) => track.stop())
          await context.close()
          return
        }
        capture.current = active
        setRecording(true)
        if (automatic) setLiveAvatar(liveFlow.current.promptComplete(turn))
        active.timer = window.setTimeout(() => stopAndTest({ automatic, turn }), 7000)
      } catch (failure) {
        stream.getTracks().forEach((track) => track.stop())
        await context?.close().catch(() => {})
        throw failure
      }
    } catch (failure) {
      if (generation === captureGeneration.current) {
        setError(failure.name === 'NotAllowedError' ? 'Microphone permission was denied' : failure.message)
        if (automatic) setLiveAvatar(liveFlow.current.fail(turn))
      }
    }
  }

  async function endCapture() {
    const active = capture.current
    if (!active) return null
    capture.current = null
    window.clearTimeout(active.timer)
    setRecording(false)
    setAvatarAudioLevel(0)
    active.processor.onaudioprocess = null
    active.processor.disconnect()
    active.source.disconnect()
    active.stream.getTracks().forEach((track) => track.stop())
    const durationMs = Date.now() - active.startedAt
    try {
      if (!active.frames) return { blob: null, durationMs }
      const audioBuffer = active.context.createBuffer(1, active.frames, active.context.sampleRate)
      const channel = audioBuffer.getChannelData(0)
      let offset = 0
      for (const chunk of active.chunks) {
        channel.set(chunk, offset)
        offset += chunk.length
      }
      return { blob: encodeAudioBufferAsWav(audioBuffer), durationMs }
    } finally {
      active.chunks = []
      await active.context.close()
    }
  }

  async function stopAndTest(options = {}) {
    const automatic = options?.automatic === true
    const turn = automatic ? options.turn : liveFlow.current.state.turn
    const generation = captureGeneration.current
    if (automatic) setLiveAvatar(liveFlow.current.captureComplete(turn))
    const submission = await action(async () => {
      const captured = await endCapture()
      if (!captured || generation !== captureGeneration.current) return
      if (captured.durationMs < 200) throw new Error('Record for at least a moment before testing')
      const wav = captured.blob
      if (generation !== captureGeneration.current) return
      if (!wav || wav.size === 0 || wav.size > 8 * 1024 * 1024 - 4096) throw new Error('Recording is empty or larger than 8 MiB')
      return submitAudio(wav)
    })
    if (automatic && submission && liveFlow.current.state.active && liveFlow.current.state.turn === turn) {
      await handleAutomaticResult(submission.value, submission.nextCoach, turn)
    } else if (automatic && liveFlow.current.state.active && liveFlow.current.state.turn === turn) {
      setLiveAvatar(liveFlow.current.fail(turn))
    }
  }

  async function handleAutomaticResult(value, nextCoach, turn) {
    const decision = value.development_result?.decision
    const resolved = liveFlow.current.resolve(turn, decision, nextCoach)
    setLiveAvatar(resolved)
    if (resolved.phase === 'PRAISE') {
      await speakLivePrompt('மிக நன்று!', turn, { allowInactive: true })
      return
    }
    if (resolved.phase !== 'COACH') return
    const selected = nextCoach.chunks[nextCoach.focusIndex] ?? nextCoach.chunks[0]
    if (!await speakLivePrompt(selected, turn)) return
    setCoach(coachFlow.current.advance())
    if (!await speakLivePrompt(nextCoach.targetWord, turn)) return
    setCoach(coachFlow.current.advance())
    setLiveAvatar(liveFlow.current.coachComplete(turn))
    if (!await speakLivePrompt(nextCoach.targetWord, turn)) return
    await startMicrophone({ automatic: true, turn })
  }

  async function startLivePractice() {
    if (!opened || !word || !selectedTarget || !runtime?.pipeline_ready || busy || recording) return
    captureGeneration.current += 1
    pending.current?.abort()
    cancelSpeech()
    await endCapture().catch(() => {})
    setError('')
    setFile(null)
    setResult(null)
    setCoach(coachFlow.current.reset())
    if (picker.current) picker.current.value = ''
    const started = liveFlow.current.start(selectedTarget)
    setLiveAvatar(started)
    if (await speakLivePrompt(selectedTarget, started.turn)) await startMicrophone({ automatic: true, turn: started.turn })
  }

  function stopLivePractice() {
    captureGeneration.current += 1
    pending.current?.abort()
    cancelSpeech()
    endCapture().catch(() => {})
    setLiveAvatar(liveFlow.current.stop())
  }

  function clear() {
    stopLivePractice()
    setFile(null)
    setResult(null)
    setCoach(coachFlow.current.reset())
    if (picker.current) picker.current.value = ''
  }

  return <>
    <section className="lab-section">
      <h2>3. Local adult audio test</h2>
      <p>Inspect the installed Tamil model with a consented adult microphone attempt or synthetic/adult WAV.</p>
      {!opened ? <>
        <label className="lab-checkbox"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /> I am the adult operator. I will use adult or synthetic test audio.</label>
        <div className="lab-actions"><button className="lab-primary" type="button" disabled={!consent || busy} onClick={() => action(open)}>Open local test session</button></div>
      </> : <>
        <div className="lab-actions"><strong>Model: {runtime?.state ?? 'Checking'}</strong><button className="lab-secondary" type="button" disabled={busy} onClick={() => action(status)}>Refresh model status</button>
          <button className="lab-secondary" type="button" disabled={busy} onClick={() => action(async () => { clear(); await labRequest('close', { method: 'POST' }); setOpened(false) })}>Close test session</button></div>
        {runtime?.reason && <p className="lab-error">{runtime.reason}</p>}
        {runtime?.state === 'loading' && <p className="lab-hint">The local model is loading. Refresh its status in a moment.</p>}
        <div className="lab-choices"><label htmlFor="diagnostic-word">Test word</label><select id="diagnostic-word" value={word} disabled={busy || recording || liveAvatar.active || !runtime?.pipeline_ready} onChange={(event) => { clear(); setWord(event.target.value) }}>
          {!runtime?.words?.length && <option value="">Waiting for model</option>}
          {runtime?.words?.map((item) => <option key={item.word_id} value={item.word_id}>{item.target_word}</option>)}</select></div>
        <div className="lab-actions"><label htmlFor="diagnostic-audio">Adult WAV (optional)</label><input ref={picker} id="diagnostic-audio" type="file" accept=".wav,audio/wav" disabled={busy || recording || liveAvatar.active || coachingBlocksAudio || !runtime?.pipeline_ready}
          onChange={(event) => { setFile(event.target.files?.[0] ?? null); setResult(null) }} /></div>
        <div className="lab-actions">
          {!recording ? <button ref={micButton} className="lab-primary" type="button" disabled={busy || liveAvatar.active || coachingBlocksAudio || !word || !runtime?.pipeline_ready || runtime?.busy} onClick={startMicrophone}>Record adult mic</button>
            : <><button className="lab-primary" type="button" onClick={stopAndTest}>Stop &amp; test</button><button className="lab-secondary" type="button" onClick={clear}>Cancel recording</button></>}
          <button className="lab-secondary" type="button" disabled={busy || recording || coachingBlocksAudio || !file || !word || !runtime?.pipeline_ready || runtime?.busy} onClick={assess}>{busy ? 'Working…' : 'Run real audio test'}</button>
          <button className="lab-secondary" type="button" onClick={clear}>Stop / clear audio</button>
        </div>
        {recording && <p role="status" className="lab-hint">Microphone recording · stop and test within 7 seconds</p>}
        <p className="lab-hint">{runtime?.words?.length ?? 0} engineering words. Speech detector: {runtime?.vad_mode ?? 'unknown'}. Test results are not saved to child progress.</p>
        <div className="lab-avatar-workspace" aria-label="Automatic avatar practice">
          <InteractiveAvatar phase={liveAvatar.phase} message={avatarMessage(liveAvatar.phase, selectedTarget)} avatarPreference={avatarPreference}
            targetWord={selectedTarget} speaking={speaking} audioLevel={avatarAudioLevel}
            active={liveAvatar.active} onStop={stopLivePractice} scopeLabel="ADULT DEVELOPMENT ONLY" />
          <div className="lab-avatar-controls">
            <h3>Automatic microphone conversation</h3>
            <p>One click starts the local sequence: prompt, listen, silence stop, model check, coaching and whole-word retry.</p>
            <button className="lab-primary" type="button" disabled={liveAvatar.active || busy || recording || !selectedTarget || !runtime?.pipeline_ready || runtime?.busy}
              onClick={startLivePractice}>{liveAvatar.active ? 'Live practice running' : 'Start live practice'}</button>
            <p className="lab-hint">{localVoice ? `Local Tamil voice: ${localVoice.name}` : 'No local Tamil voice found — prompts use a visible timed fallback before listening.'}</p>
          </div>
        </div>
      </>}
      {error && <p role="alert" className="lab-error">{error}</p>}
      {result && <div className="lab-live-result" aria-label="Real audio result">
        <strong className="lab-source">REAL MODEL · ADULT ENGINEERING EVIDENCE</strong>
        <p className="lab-preview">Development result: <strong>{{
          DEV_MATCH: 'MATCH', DEV_TRY_AGAIN: 'TRY AGAIN', DEV_UNCERTAIN: 'UNCERTAIN — RETRY',
          DEV_UNAVAILABLE: 'RECORD AGAIN',
        }[result.development_result?.decision] ?? 'RECORD AGAIN'}</strong></p>
        {result.adult_preview?.status === 'provisional' && typeof result.adult_preview.estimate === 'number'
          ? <p className="lab-preview">Provisional adult match estimate: <strong>{Math.round(result.adult_preview.estimate * 100)}%</strong></p>
          : <p className="lab-hint">No estimate: {result.adult_preview?.reason_code ?? 'adult preview unavailable'}</p>}
        <p className="lab-hint">This is a model inspection, not a pronunciation diagnosis. A candidate is a recognition hypothesis, not proof that every sound was correct.</p>
        <dl className="lab-result-rows">{[
          ['Target word', result.result.target_word ?? runtime?.words?.find((item) => item.word_id === word)?.target_word ?? 'unavailable'],
          ['Model candidate', result.result.observed_candidates?.[0]?.word ?? 'No model candidate'],
          ['Candidate confidence', result.result.observed_candidates?.[0]?.probability ?? 'unavailable'],
          ['Speech detected', result.result.quality?.speech_detected == null ? 'unavailable' : result.result.quality.speech_detected ? 'Yes' : 'No'],
          ['Capture duration', typeof result.result.quality?.duration_s === 'number' ? `${result.result.quality.duration_s.toFixed(1)} s` : 'unavailable'],
          ['Capture quality', result.result.quality?.reason ?? (result.result.quality?.valid ? 'Valid engineering capture' : 'unavailable')],
          ['Development action', result.development_result?.avatar_state ?? 'RECAPTURE'],
          ['Development band', result.development_result?.band_version ?? 'unavailable'],
          ['Raw word evidence', result.result.evidence.original_asr.target_probability ?? 'unavailable'],
          ['Normalized word evidence', result.result.evidence.normalized_asr?.target_probability ?? 'unavailable'],
          ['Classifier evidence', result.result.evidence.word_classifier.target_probability ?? 'unavailable'],
          ['Reference similarity', result.result.evidence.embedding_dtw.similarity ?? 'unavailable'],
          ['Latency', `${result.result.latency_ms} ms`], ['Calibration', result.result.calibration_version],
        ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
        <p className="lab-hint">Adult development result only. The percentage is an engineering index, not measured accuracy or a child score. The product scoring channel is isolated from this lab. No child score or pronunciation diagnosis.</p>
      </div>}
      <AdultChunkCoach coach={coach} localVoice={localVoice} speaking={speaking}
        onSelect={(index) => setCoach(coachFlow.current.select(index))}
        onAdvance={() => setCoach(coachFlow.current.advance())}
        onReset={() => { cancelSpeech(); setCoach(coachFlow.current.reset()); setResult(null) }}
        onSpeak={speakExample}
        onGoToRecording={() => { micButton.current?.scrollIntoView({ block: 'center' }); micButton.current?.focus() }} />
    </section>
    <section className="lab-section lab-last">
      <h2>4. Verify the session lifecycle</h2><p>Exercise the real database with temporary synthetic session records.</p>
      <button className="lab-primary" type="button" disabled={!opened || busy} onClick={() => action(async () => setChecks(await labRequest('session-checks', { method: 'POST', signal: AbortSignal.timeout(30000) })))}>Run session checks</button>
      {checks && <div aria-label="Session checks" className="lab-live-result"><strong className="lab-source">SYNTHETIC MODEL · REAL DATABASE</strong>
        <dl className="lab-result-rows">{checks.checks.map((item) => <div key={item.name}><dt>{item.passed ? 'Passed' : 'Failed'}</dt><dd>{item.name}</dd></div>)}</dl></div>}
    </section>
  </>
}
