import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Cat,
  Heart,
  Mic,
  MicOff,
  MessageCircle,
  RotateCcw,
  Sparkles,
  Volume2,
  VolumeX,
} from 'lucide-react'
import { getPetMood, getPetResponse, getSpeechRecognitionConstructor } from './petLogic'

const MAX_HISTORY = 5

function App() {
  const [transcript, setTranscript] = useState('')
  const [draft, setDraft] = useState('')
  const [lastResponse, setLastResponse] = useState('Say something and I will repeat it!')
  const [history, setHistory] = useState([])
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [notice, setNotice] = useState('Tap the microphone and talk to Pippin')
  const [petCount, setPetCount] = useState(0)
  const recognitionRef = useRef(null)
  const responseRef = useRef('')
  const noticeTimerRef = useRef(null)

  const SpeechRecognition = useMemo(() => getSpeechRecognitionConstructor(), [])
  const supportsListening = Boolean(SpeechRecognition)
  const mood = getPetMood({ isListening, isSpeaking, hasTranscript: Boolean(transcript) })

  const showNotice = useCallback((message) => {
    setNotice(message)
    if (noticeTimerRef.current) window.clearTimeout(noticeTimerRef.current)
    noticeTimerRef.current = window.setTimeout(() => setNotice('Tap the microphone and talk to Pippin'), 3200)
  }, [])

  const speak = useCallback((text) => {
    const phrase = String(text || '').trim()
    if (!phrase) return
    responseRef.current = phrase
    setLastResponse(phrase)
    if (isMuted || !('speechSynthesis' in window)) {
      showNotice(isMuted ? 'Sound is muted. Tap the speaker to hear Pippin.' : 'Your browser cannot play voice audio.')
      return
    }

    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(phrase)
    utterance.lang = 'en-IN'
    utterance.rate = 0.92
    utterance.pitch = 1.2
    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)
    window.speechSynthesis.speak(utterance)
  }, [isMuted, showNotice])

  const recordPhrase = useCallback((phrase) => {
    const cleanPhrase = String(phrase || '').trim()
    if (!cleanPhrase) return
    const response = getPetResponse(cleanPhrase)
    setTranscript(cleanPhrase)
    setHistory((items) => [{ heard: cleanPhrase, repeated: response, id: Date.now() }, ...items].slice(0, MAX_HISTORY))
    speak(response)
    showNotice('Pippin repeated it!')
  }, [showNotice, speak])

  const startListening = useCallback(() => {
    if (!SpeechRecognition) {
      showNotice('Voice input is unavailable. Type a phrase below instead.')
      return
    }

    if (isListening) {
      recognitionRef.current?.stop()
      return
    }

    const recognition = new SpeechRecognition()
    recognition.lang = 'en-IN'
    recognition.continuous = false
    recognition.interimResults = true
    recognition.onstart = () => {
      setIsListening(true)
      setTranscript('')
      showNotice('Listening… speak naturally')
    }
    recognition.onresult = (event) => {
      let phrase = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        phrase += event.results[i][0].transcript
      }
      setTranscript(phrase.trim())
      const finalResult = Array.from(event.results).some((result) => result.isFinal)
      if (finalResult && phrase.trim()) recordPhrase(phrase)
    }
    recognition.onerror = (event) => {
      setIsListening(false)
      showNotice(event.error === 'not-allowed' ? 'Microphone permission is needed to listen.' : 'I missed that. Please try again.')
    }
    recognition.onend = () => {
      setIsListening(false)
      recognitionRef.current = null
    }
    recognitionRef.current = recognition
    recognition.start()
  }, [SpeechRecognition, isListening, recordPhrase, showNotice])

  const repeatDraft = () => {
    const phrase = draft.trim()
    if (!phrase) {
      showNotice('Type a phrase first, then tap Repeat')
      return
    }
    recordPhrase(phrase)
    setDraft('')
  }

  const handlePet = () => {
    setPetCount((count) => count + 1)
    showNotice(petCount % 2 === 0 ? 'Pippin loves gentle pats! 💛' : 'That tickles!')
  }

  const reset = () => {
    recognitionRef.current?.stop()
    window.speechSynthesis?.cancel()
    setTranscript('')
    setLastResponse('Say something and I will repeat it!')
    setHistory([])
    setIsListening(false)
    setIsSpeaking(false)
    showNotice('Ready for a fresh conversation')
  }

  useEffect(() => () => {
    recognitionRef.current?.stop()
    window.speechSynthesis?.cancel()
    if (noticeTimerRef.current) window.clearTimeout(noticeTimerRef.current)
  }, [])

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-icon"><Cat size={22} /></div>
          <div>
            <p className="brand-name">Pippin</p>
            <p className="brand-subtitle">your talking pet</p>
          </div>
        </div>
        <div className="top-actions">
          <button className="icon-button" type="button" onClick={() => setIsMuted((value) => !value)} aria-label={isMuted ? 'Turn sound on' : 'Mute sound'}>
            {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
          </button>
          <button className="icon-button" type="button" onClick={reset} aria-label="Reset conversation"><RotateCcw size={19} /></button>
        </div>
      </header>

      <section className="hero-grid">
        <div className="intro-copy">
          <p className="eyebrow"><Sparkles size={15} /> listen · repeat · smile</p>
          <h1>Say anything.<br /><span>Pippin repeats it.</span></h1>
          <p className="intro-text">A gentle little friend for practising words, sounds, and confidence. Tap the mic, speak, and hear your words come back.</p>
          <div className="feature-row">
            <span><MessageCircle size={16} /> speech repeat</span>
            <span><Heart size={16} /> playful reactions</span>
          </div>
        </div>

        <div className={`pet-stage mood-${mood}`}>
          <div className="stage-glow" />
          <div className="pet-card" onClick={handlePet} role="button" tabIndex={0} onKeyDown={(event) => event.key === 'Enter' && handlePet()} aria-label="Pet Pippin">
            <div className="pet-ribbon">{isListening ? 'listening' : isSpeaking ? 'talking' : 'ready'}</div>
            <img src="/pippin-mascot.png" alt="Pippin, an original orange kitten" className="pet-image" />
            <div className="pet-sparkles" aria-hidden="true"><span>✦</span><span>✧</span><span>✦</span></div>
            <div className="pet-speech">
              <span className="speech-dot" />
              <span>{lastResponse}</span>
            </div>
            {(isSpeaking || isListening) && <div className="sound-bars" aria-label={isListening ? 'Pippin is listening' : 'Pippin is speaking'}>{[1, 2, 3, 4, 5].map((bar) => <i key={bar} />)}</div>}
          </div>
          <p className="pet-hint">Tap Pippin for a pat</p>
        </div>
      </section>

      <section className="interaction-panel" aria-label="Talk to Pippin">
        <div className="panel-heading">
          <div>
            <p className="panel-kicker">Your turn</p>
            <h2>{notice}</h2>
          </div>
          <span className={`status-dot ${supportsListening ? 'available' : 'fallback'}`}><span /> {supportsListening ? 'mic ready' : 'type mode'}</span>
        </div>

        <button className={`listen-button ${isListening ? 'active' : ''}`} type="button" onClick={startListening} aria-pressed={isListening}>
          {isListening ? <MicOff size={24} /> : <Mic size={24} />}
          <span>{isListening ? 'Stop listening' : 'Tap to talk'}</span>
          <small>{isListening ? 'I am listening…' : 'Pippin will repeat you'}</small>
        </button>

        <div className="fallback-row">
          <input value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && repeatDraft()} placeholder="Or type something for Pippin…" aria-label="Type a phrase for Pippin" />
          <button type="button" onClick={repeatDraft}>Repeat</button>
        </div>
        <p className="privacy-note">Your voice stays in this browser. Nothing is uploaded.</p>
      </section>

      <section className="history-section">
        <div className="section-heading"><h2>Recent repeats</h2><span>{history.length} / {MAX_HISTORY}</span></div>
        {history.length === 0 ? (
          <div className="empty-state"><MessageCircle size={19} /><span>Your repeated phrases will appear here.</span></div>
        ) : (
          <div className="history-list">{history.map((item) => <div className="history-item" key={item.id}><span className="heard-label">You</span><p>{item.heard}</p><span className="repeat-arrow">→</span><span className="heard-label pippin-label">Pippin</span><p>{item.repeated}</p></div>)}</div>
        )}
      </section>
      <footer>Made for gentle practice · <strong>Pippin</strong> is an original character</footer>
    </main>
  )
}

export default App
