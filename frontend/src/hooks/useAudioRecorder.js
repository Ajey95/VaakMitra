import { useState, useRef, useCallback } from 'react'
import toast from 'react-hot-toast'
import { repeatPhrase } from '../utils/speechRepeat'

export const useAudioRecorder = () => {
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState(null)
  const [duration, setDuration] = useState(0)
  const [isRepeating, setIsRepeating] = useState(false)
  
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])
  const startTimeRef = useRef(null)
  const recognitionRef = useRef(null)
  const lastRepeatedRef = useRef('')
  const repeatTimeoutRef = useRef(null)
  const captureGenerationRef = useRef(0)
  const [transcript, setTranscript] = useState('')

  // Web Audio nodes for real-time visualization. Exposed via analyserRef so
  // consumers can run their own requestAnimationFrame loop without re-rendering.
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)

  const teardownAudioGraph = useCallback(() => {
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {})
      audioContextRef.current = null
    }
    analyserRef.current = null
  }, [])

  const startRecording = useCallback(async (language = 'en-IN', options = {}) => {
    const generation = captureGenerationRef.current
    try {
      lastRepeatedRef.current = ''
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (generation !== captureGenerationRef.current) {
        stream.getTracks().forEach((track) => track.stop())
        return false
      }
      streamRef.current = stream

      // Initialize MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      })

      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []
      startTimeRef.current = Date.now()

      // ── Real-time analyser for the live waveform / volume meter ──
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext
        const audioContext = new AudioCtx()
        const source = audioContext.createMediaStreamSource(stream)
        const analyser = audioContext.createAnalyser()
        analyser.fftSize = 256
        analyser.smoothingTimeConstant = 0.7
        source.connect(analyser)
        audioContextRef.current = audioContext
        analyserRef.current = analyser
      } catch (e) {
        console.warn('AnalyserNode unavailable, waveform will idle:', e)
      }

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        if (generation === captureGenerationRef.current) {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
          setAudioBlob(blob)
          setDuration(Date.now() - startTimeRef.current)
        }

        // Stop all tracks and release the audio graph
        stream.getTracks().forEach(track => track.stop())
        if (streamRef.current === stream) streamRef.current = null
        if (mediaRecorderRef.current === mediaRecorder) teardownAudioGraph()
      }

      mediaRecorder.start()
      setIsRecording(true)

      // Initialize Speech Recognition if available
      if (options.speechRecognition !== false && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
        const recognition = new SpeechRecognition()

        recognition.continuous = false
        recognition.interimResults = true  // live partial transcript
        recognition.lang = language

        recognition.onresult = (event) => {
          // Concatenate all results so the bubble updates live as the child speaks
          let text = ''
          let hasFinalResult = false
          for (let i = 0; i < event.results.length; i++) {
            text += event.results[i][0].transcript
            hasFinalResult = hasFinalResult || event.results[i].isFinal
          }
          const phrase = text.trim()
          setTranscript(phrase)

          // Repeat the child's exact words as soon as recognition confirms the phrase.
          if (options.repeatRecognized !== false && hasFinalResult && phrase && phrase !== lastRepeatedRef.current) {
            window.clearTimeout(repeatTimeoutRef.current)
            setIsRepeating(true)
            const finishRepeat = () => setIsRepeating(false)
            const repeated = repeatPhrase(phrase, {
              lang: language,
              onStart: () => setIsRepeating(true),
              onEnd: finishRepeat,
              onError: finishRepeat,
            })
            if (repeated) {
              lastRepeatedRef.current = phrase
              repeatTimeoutRef.current = window.setTimeout(finishRepeat, 4000)
            } else {
              finishRepeat()
            }
          }
        }

        recognition.onerror = (event) => {
          console.error('Speech recognition error:', event.error)
        }

        recognitionRef.current = recognition
        recognition.start()
      }

      return true
    } catch (error) {
      console.error('Error starting recording:', error)
      toast.error('Could not access microphone')
      return false
    }
  }, [teardownAudioGraph])
  
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [])
  
  const resetRecording = useCallback(() => {
    captureGenerationRef.current += 1
    if (mediaRecorderRef.current?.state && mediaRecorderRef.current.state !== 'inactive') {
      try { mediaRecorderRef.current.stop() } catch { /* already stopping */ }
    }
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (recognitionRef.current) {
      try { recognitionRef.current.stop() } catch { /* already stopped */ }
      recognitionRef.current = null
    }
    setIsRecording(false)
    setAudioBlob(null)
    setDuration(0)
    setTranscript('')
    setIsRepeating(false)
    window.clearTimeout(repeatTimeoutRef.current)
    lastRepeatedRef.current = ''
    window.speechSynthesis?.cancel()
    chunksRef.current = []
    teardownAudioGraph()
  }, [teardownAudioGraph])

  return {
    isRecording,
    audioBlob,
    duration,
    transcript,
    isRepeating,
    analyserRef,
    startRecording,
    stopRecording,
    resetRecording
  }
}
