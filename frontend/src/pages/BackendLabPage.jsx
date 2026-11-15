import { useEffect, useRef, useState } from 'react'
import { Activity, AudioLines, BookOpen, FlaskConical, FolderOpen, Home, Play, Settings2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { loadVocabulary, probeHealth } from '../features/backendLab/labClient'
import { simulationFor } from '../features/backendLab/fixtures'
import DiagnosticPanel from '../features/backendLab/DiagnosticPanel'
import './BackendLabPage.css'

const CHECKS = [
  { key: 'live', title: 'Process' },
  { key: 'ready', title: 'Database' },
  { key: 'scoring', title: 'Scoring' },
]

function healthLabel(row, key) {
  if (!row) return 'Not checked'
  if (row.status === null) return row.reasons[0] === 'TIMED_OUT' ? 'Timed out' : 'Unreachable'
  return `${row.status} ${row.ready ? key === 'live' ? 'Alive' : 'Ready' : 'Blocked'}`
}

function ResultRows({ result }) {
  return (
    <dl className="lab-result-rows">
      <div><dt>Decision</dt><dd>{result.decision}</dd></div>
      <div><dt>Reason</dt><dd>{result.reason_code}</dd></div>
      <div><dt>Response intent</dt><dd>{result.response_intent}</dd></div>
      <div><dt>Avatar state</dt><dd>{result.avatar_state}</dd></div>
      <div><dt>Next exercise</dt><dd>{result.next_exercise_id ?? 'none'}</dd></div>
    </dl>
  )
}

export default function BackendLabPage() {
  const user = useAuthStore((state) => state.user)
  const [health, setHealth] = useState(null)
  const [checkedAt, setCheckedAt] = useState(null)
  const [vocabulary, setVocabulary] = useState(null)
  const [simulationKey, setSimulationKey] = useState('')
  const [busy, setBusy] = useState(false)
  const controller = useRef(null)

  useEffect(() => () => controller.current?.abort(), [])

  // PRV-002/UX-007: diagnostic data must never enter a child's plan-backed session.
  const operator = ['admin', 'therapist'].includes(user?.role)
  const entries = operator ? vocabulary?.entries ?? [] : []
  const scoreable = entries.filter((entry) => entry.available_for_scoring)
  const simulation = simulationKey ? simulationFor(simulationKey) : null

  async function runLiveCheck() {
    controller.current?.abort()
    const active = new AbortController()
    controller.current = active
    setBusy(true)
    setSimulationKey('')
    try {
      const [checks, registry] = await Promise.all([probeHealth(fetch, active.signal), loadVocabulary(fetch, active.signal)])
      if (active.signal.aborted) return
      setHealth(checks)
      setCheckedAt(new Date().toLocaleString())
      setVocabulary(registry)
    } finally {
      if (controller.current === active) setBusy(false)
    }
  }

  return (
    <div className="lab-shell">
      <aside className="lab-sidebar" aria-label="Development navigation">
        <Link className="lab-brand" to="/"><AudioLines size={31} strokeWidth={2.5} /><span>VaakMitra</span></Link>
        <nav>
          <Link to="/"><Home size={18} /> Home</Link>
          <Link to="/play"><FolderOpen size={18} /> Sessions</Link>
          <Link to="/progress"><Activity size={18} /> Progress</Link>
          <Link to="/videos"><BookOpen size={18} /> Resources</Link>
          <span className="lab-nav-current"><FlaskConical size={18} /> Engineering Lab</span>
        </nav>
        <Link className="lab-sidebar-settings" to="/settings"><Settings2 size={18} /> Settings</Link>
      </aside>

      <main className="lab-main">
        <header className="lab-heading">
          <div><span className="lab-warning">ENGINEERING ONLY</span><h1>Backend Verification Lab</h1><p>Diagnostic tools for backend services, authentication, and response contracts.</p></div>
          <span className="lab-private-note">Isolated tool. Not part of child experience.</span>
        </header>

        <div className="lab-columns">
          <div className="lab-live-panel">
            <section className="lab-section">
              <div className="lab-section-heading"><div><h2>1. Live backend checks</h2><p>Check availability of core backend services.{checkedAt && ` Last live check: ${checkedAt}.`}</p></div><button className="lab-primary" type="button" onClick={runLiveCheck} disabled={busy}><Play size={16} fill="currentColor" /> Run live check</button></div>
              <div className="lab-health-grid">
                {CHECKS.map(({ key, title }) => {
                  const row = health?.[key]
                  return <div className="lab-health" key={key}><span className={`lab-dot ${row?.ready ? 'is-good' : row ? 'is-bad' : ''}`} /><div><h3>{title} <span className={row?.ready ? 'is-good-text' : row ? 'is-bad-text' : ''}>· {healthLabel(row, key)}</span></h3><p>{row ? row.reasons[0] ?? `${title} service responding.` : 'Run a live check to inspect this service.'}</p>{row && <small>Live · {row.latencyMs} ms</small>}</div></div>
                })}
              </div>
              {health?.scoring?.reasons?.length > 0 && <div className="lab-reason"><strong>{health.scoring.reasons.join(', ')}</strong><span>Scoring is unavailable until all required artifacts are approved.</span></div>}
            </section>

            <section className="lab-section">
              <h2>2. Authentication &amp; vocabulary</h2><p>Verify access to protected resources.</p>
              <div className="lab-health-grid lab-two">
                <div className="lab-health"><span className={`lab-dot ${vocabulary?.ready && operator ? 'is-good' : vocabulary ? 'is-bad' : ''}`} /><div><h3>{vocabulary?.ready && !operator ? 'Operator authorization required' : vocabulary?.ready ? 'Authenticated operator' : vocabulary?.status === 401 ? 'Authentication required' : vocabulary ? 'Authentication unavailable' : 'Not checked'}</h3><p>{vocabulary?.ready && !operator ? 'Use an admin or therapist account for diagnostic audio.' : vocabulary?.ready ? 'Protected vocabulary was returned.' : vocabulary?.status === 401 ? 'Sign in as an adult operator to test protected endpoints.' : 'Run a live check to verify access.'}</p></div></div>
                <div className="lab-health"><span className={`lab-dot ${vocabulary?.ready && operator ? 'is-good' : vocabulary ? 'is-bad' : ''}`} /><div><h3>{vocabulary?.ready && operator ? 'Vocabulary loaded' : 'Vocabulary unavailable'}</h3><p>{vocabulary?.ready && operator ? `${scoreable.length} scoreable / ${entries.length} listed` : vocabulary?.ready ? 'Operator-only diagnostic registry.' : vocabulary?.reasons?.[0] ?? 'No registry observation yet.'}</p></div></div>
              </div>
              {vocabulary?.ready && operator && <p className="lab-hint">The registry lists {entries.length} words; availability does not establish clinical scoring readiness.</p>}
            </section>

            <DiagnosticPanel />
          </div>

          <aside className="lab-simulation" aria-label="Contract simulation">
            <div className="lab-sim-heading"><div><FlaskConical size={21} /><h2>Contract simulation</h2></div><strong>SIMULATED — NO BACKEND CALL</strong></div>
            <p>Explore governed response states with static examples. These are never model or child-validation evidence.</p>
            <div className="lab-sim-info">This mode does not call any backend service.</div>
            <label htmlFor="lab-simulation">Simulated decision</label>
            <select id="lab-simulation" value={simulationKey} disabled={busy} onChange={(event) => { controller.current?.abort(); setBusy(false); setSimulationKey(event.target.value) }}>
              <option value="">Select a simulated state</option><option value="pass">PASS</option><option value="retry">RETRY</option><option value="invalid">UNSCORABLE · invalid capture</option><option value="capability">UNSCORABLE · missing model</option>
            </select>
            {simulation ? <div className="lab-sim-result"><ResultRows result={simulation.result} /></div> : <div className="lab-sim-placeholder">Choose a state to preview its safe response contract.</div>}
            <div className="lab-sim-info lab-sim-footer">Live checks on the left are separate. No simulation result is a clinical score.</div>
          </aside>
        </div>
      </main>
    </div>
  )
}
