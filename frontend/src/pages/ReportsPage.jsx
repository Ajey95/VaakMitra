import { useQuery } from '@tanstack/react-query'
import { FileText, Printer } from 'lucide-react'
import DashboardLayout from '../components/layout/DashboardLayout'
import { canonicalWordClient } from '../services/api'

const decisionLabels = {
  PASS: 'Matched the target word',
  RETRY: 'Practised this word again',
  UNSCORABLE: 'Could not assess this capture',
}

const reasonLabels = {
  INVALID_AUDIO: 'Audio quality prevented an assessment',
  CALIBRATION_UNAVAILABLE: 'Word checker was unavailable',
  MODEL_UNAVAILABLE: 'Word checker was unavailable',
  MODEL_TIMEOUT: 'Word check timed out',
  CALIBRATED_WORD_MISMATCH: 'The whole word needs another try',
}

const eventLabels = {
  break_started: 'Break started',
  break_ended: 'Break ended',
  session_resumed: 'Session resumed',
  session_ended: 'Session ended',
}

function elapsed(second) {
  if (!Number.isInteger(second) || second < 0) return 'time unavailable'
  return `${Math.floor(second / 60)}:${String(second % 60).padStart(2, '0')}`
}

function Count({ label, value, denominator }) {
  return <div className="rounded-2xl border border-neutral-200 bg-white p-4 dark:border-neutral-700 dark:bg-neutral-900">
    <dt className="text-sm text-neutral-500 dark:text-neutral-400">{label}</dt>
    <dd className="mt-1 text-2xl font-bold text-neutral-900 dark:text-white">
      {Number.isInteger(value) ? value : 'Unavailable'}{Number.isInteger(value) && Number.isInteger(denominator) ? <span className="text-base font-medium text-neutral-500"> / {denominator}</span> : null}
    </dd>
  </div>
}

function SessionReport({ report }) {
  const metrics = report.metrics || {}
  const timeline = Array.isArray(report.timeline) ? report.timeline : []
  return <article className="rounded-3xl border border-neutral-200 bg-neutral-50 p-5 dark:border-neutral-700 dark:bg-neutral-900/50" aria-label={`Session ${report.session_id}`}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-xl font-bold text-neutral-900 dark:text-white">Word session</h2>
        <p className="mt-1 text-sm text-neutral-500">{report.session_id} · {report.status}</p>
      </div>
      <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-900" aria-label="Therapist review not signed">Therapist review not signed</span>
    </div>

    <dl className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Count label="Words attempted" value={metrics.attempted_words} denominator={metrics.planned_words} />
      <Count label="First scoreable word passes" value={metrics.first_scoreable_pass_words} denominator={metrics.scoreable_words} />
      <Count label="Words passed after practice" value={metrics.eventual_pass_words} denominator={metrics.scoreable_words} />
      <Count label="Captures not assessable" value={metrics.unscorable_attempts} denominator={metrics.total_captures} />
    </dl>

    <div className="mt-6">
      <h3 className="font-bold text-neutral-900 dark:text-white">How the session went</h3>
      {timeline.length ? <ol className="mt-3 space-y-2">
        {timeline.map((event) => <li key={event.ordinal} className="rounded-xl bg-white p-3 text-sm dark:bg-neutral-900">
          <span className="font-semibold">{event.ordinal}. {report.word_labels?.[event.word_id] || event.word_id}</span>
          <span className="mx-2 text-neutral-400" aria-hidden="true">·</span>
          <span>{decisionLabels[event.decision] || 'Assessment unavailable'}</span>
          {event.reason_code && event.decision !== 'PASS' ? <p className="mt-1 text-neutral-500">{reasonLabels[event.reason_code] || event.reason_code.replaceAll('_', ' ').toLowerCase()}</p> : null}
        </li>)}
      </ol> : <p className="mt-2 text-sm text-neutral-500">No completed word attempts were recorded.</p>}
    </div>

    <div className="mt-5 text-sm text-neutral-600">
      <h3 className="font-bold text-neutral-900 dark:text-white">Breaks and ending</h3>
      {report.break_data_status === 'unavailable_legacy' ? <p className="mt-2">Break details are unavailable for this older session.</p>
        : Array.isArray(report.session_events) && report.session_events.length
          ? <ul className="mt-2 space-y-1">{report.session_events.map((event, index) => <li key={`${event.type}-${index}`}>{eventLabels[event.type] || 'Session event'} at {elapsed(event.session_second)}</li>)}</ul>
          : <p className="mt-2">No break or stop event was recorded.</p>}
    </div>
    <p className="mt-2 text-xs text-neutral-500">These are whole-word practice events, not a pronunciation diagnosis or therapist-approved follow-up plan.</p>
  </article>
}

export default function ReportsPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['word-session-reports'],
    queryFn: async () => (await canonicalWordClient.get('/api/v1/word-session-reports')).data,
    retry: false,
  })
  const reports = Array.isArray(data?.reports) ? data.reports.filter((report) => report?.schema_version === 'word-session-report-1') : []
  const actions = <button type="button" onClick={() => window.print()} className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-neutral-900 hover:bg-neutral-100"><Printer className="h-4 w-4" aria-hidden="true" /> Save as PDF</button>

  return <DashboardLayout title="Word practice reports" subtitle="A record of completed whole-word sessions" icon={FileText} actions={actions}>
    {isLoading ? <p role="status" className="rounded-2xl bg-white p-6 text-neutral-600">Loading reports…</p>
      : isError ? <div role="alert" className="rounded-2xl bg-white p-6 text-neutral-700"><p>Reports are unavailable right now.</p><button type="button" onClick={() => refetch()} className="mt-3 rounded-xl bg-neutral-900 px-4 py-2 text-white">Try again</button></div>
        : reports.length === 0 ? <div className="rounded-2xl bg-white p-8 text-center text-neutral-700" role="status"><h2 className="text-xl font-bold">No word-session report yet</h2><p className="mt-2">Completed practice sessions will appear here. No scores are estimated.</p></div>
          : <div className="space-y-6">{reports.map((report) => <SessionReport key={report.session_id} report={report} />)}</div>}
  </DashboardLayout>
}
