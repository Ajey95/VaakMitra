import { useEffect, useReducer, useRef, useState } from 'react'
import { ArrowRight, Check, HandHeart, SkipForward } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import CaregiverPromptPanel from '../components/interactive/CaregiverPromptPanel'
import ChildFeedback from '../components/interactive/ChildFeedback'
import InteractiveSessionShell from '../components/interactive/InteractiveSessionShell'
import { CelebrationLayer, TamilStatus } from '../components/interactive/SceneEffects'
import {
  TALK_TOGETHER_ACTIVITY,
  TALK_TOGETHER_MISSIONS,
  advanceMission,
  buildTalkTogetherReport,
} from '../features/together/talkTogetherActivity'
import { createSession, sessionReducer } from '../features/interactive/sessionEngine'
import { getEffectProfile, getTamilPrompt, getTalkTogetherReward } from '../features/interactive/animationPresentation'
import { createSceneAudioController } from '../features/interactive/sceneAudio'
import { interactiveSessionsAPI } from '../services/api'
import { useInteractionSettingsStore } from '../store/interactionSettingsStore'

export default function TalkTogetherPage() {
  const navigate = useNavigate()
  const [session, dispatch] = useReducer(sessionReducer, TALK_TOGETHER_ACTIVITY, createSession)
  const [missionIndex, setMissionIndex] = useState(0)
  const [mode, setMode] = useState('mission')
  const [assistance, setAssistance] = useState('independent')
  const [lastAssistance, setLastAssistance] = useState('independent')
  const [events, setEvents] = useState([])
  const startedAtRef = useRef(Date.now())
  const sceneAudioRef = useRef(null)
  const { preferences } = useInteractionSettingsStore()
  const mission = TALK_TOGETHER_MISSIONS[missionIndex]
  const reward = getTalkTogetherReward(lastAssistance)
  const celebrationLevel = reward.intensity === 'none' || preferences.celebrationLevel === 'none'
    ? 'none'
    : reward.intensity === 'gentle'
      ? 'gentle'
      : preferences.celebrationLevel
  const effectProfile = getEffectProfile({ ...preferences, celebrationLevel })

  if (!sceneAudioRef.current && typeof window !== 'undefined') sceneAudioRef.current = createSceneAudioController(window)

  useEffect(() => () => sceneAudioRef.current?.stop(), [])

  useEffect(() => {
    if (!preferences.soundEnabled) sceneAudioRef.current?.stop()
  }, [preferences.soundEnabled])

  const saveCompletion = (finalEvents) => {
    const report = buildTalkTogetherReport({ startedAt: startedAtRef.current, completedAt: Date.now(), events: finalEvents })
    interactiveSessionsAPI.create(report).catch(() => {})
  }

  const confirmTurn = (level = assistance) => {
    const event = { missionId: mission.id, assistance: level }
    const finalEvents = [...events, event]
    setEvents(finalEvents)
    setLastAssistance(level)
    dispatch({ type: 'BEGIN_ATTEMPT', at: Date.now() })
    if (level === 'skipped') dispatch({ type: 'SKIP', at: Date.now() })
    else {
      dispatch({ type: 'RESPONSE_CAPTURED', response: { caregiverConfirmed: true }, at: Date.now() })
      dispatch({ type: 'EVALUATION_SUCCEEDED', assistance: level, at: Date.now() })
    }
    const next = advanceMission({ missionIndex, complete: false })
    if (level !== 'skipped') {
      const spokenPrompt = next.complete ? getTamilPrompt('talk-together', 'complete') : mission.celebrateTa
      sceneAudioRef.current?.speakTamil(spokenPrompt, { enabled: preferences.soundEnabled && preferences.spokenPrompts, activated: true })
      sceneAudioRef.current?.playEffect('sticker', { enabled: preferences.soundEnabled, activated: true })
    }
    if (next.complete) {
      dispatch({ type: 'COMPLETE', at: Date.now() })
      saveCompletion(finalEvents)
      setMode('complete')
    } else setMode('celebrate')
  }

  const nextMission = () => {
    dispatch({ type: 'NEXT_STEP', at: Date.now() })
    setMissionIndex((current) => current + 1)
    setAssistance('independent')
    setMode('mission')
  }

  return (
    <InteractiveSessionShell title="Talk Together" subtitle="Five playful turns with a trusted grown-up" state={session} dispatch={dispatch} steps={TALK_TOGETHER_ACTIVITY.steps}>
      <div className="together-wrap">
        <div className="together-environment" data-environment={mission.environment} style={{ '--environment-index': mission.environmentIndex }} aria-hidden="true">
          <div className="together-environment__strip"><img src="/assets/interactive/talk-together/talk-together-environments.png" alt="" /></div>
          <img className="together-characters" src="/assets/interactive/talk-together/talk-together-characters.png" alt="" />
          <span className="together-turn-glow" />
        </div>

        {mode === 'mission' ? (
          <div className="together-card" data-mode="mission">
            <span className="together-card__number">Mission {missionIndex + 1} of 5</span>
            <div className="together-card__prop" aria-hidden="true">{mission.icon}</div>
            <div className="together-card__copy"><span>{mission.title}</span><h2>{mission.childPrompt}</h2><p>Words, gestures, pictures, and sounds all count as communication.</p></div>
            <CaregiverPromptPanel mission={mission} assistance={assistance} onAssistanceChange={setAssistance} />
            <div className="together-actions">
              <button className="interactive-control together-button together-button--primary" type="button" onClick={() => confirmTurn(assistance)}><Check aria-hidden="true" /> We had a turn</button>
              <button className="interactive-control together-button together-button--quiet" type="button" onClick={() => confirmTurn('skipped')}><SkipForward aria-hidden="true" /> Skip gently</button>
            </div>
          </div>
        ) : null}

        {mode === 'celebrate' ? (
          <div className="together-card together-card--celebrate">
            <div className="together-card__prop" aria-hidden="true"><HandHeart /></div>
            <ChildFeedback kind="success" title={mission.celebrateTa} detail={`${mission.celebrate} A shared turn is worth celebrating.`} />
            <TamilStatus label={mission.celebrateTa} />
            <CelebrationLayer variant="stickers" state="celebrate" effectProfile={effectProfile} />
            <button className="interactive-control together-button together-button--primary" type="button" onClick={nextMission}>Next mission <ArrowRight aria-hidden="true" /></button>
          </div>
        ) : null}

        {mode === 'complete' ? (
          <div className="together-card together-card--complete">
            <div className="together-sticker-board" aria-hidden="true">{TALK_TOGETHER_MISSIONS.map((item) => <i key={item.id}>{item.icon}</i>)}</div>
            <ChildFeedback kind="success" title={getTamilPrompt('talk-together', 'complete')} detail="You talked together! Five small missions created five meaningful communication opportunities." />
            <TamilStatus label={getTamilPrompt('talk-together', 'complete')} />
            <CelebrationLayer variant="balloons" state="complete" effectProfile={effectProfile} />
            <button className="interactive-control together-button together-button--primary" type="button" onClick={() => navigate('/play')}>Choose another adventure</button>
          </div>
        ) : null}
      </div>
    </InteractiveSessionShell>
  )
}
