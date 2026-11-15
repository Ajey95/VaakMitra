import { AlertCircle, HandHeart, MessageCircle, Sparkles, TrendingUp } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { formatInteractiveSummary } from '../../features/interactive/parentSummary'
import { interactiveSessionsAPI } from '../../services/api'

export default function InteractivePracticeSummary() {
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['interactivePracticeSummary'],
    queryFn: () => interactiveSessionsAPI.summary(),
    staleTime: 30_000,
  })

  if (isPending) {
    return <section className="parent-practice parent-practice--loading" aria-label="Loading Play and Practice summary"><span /><span /><span /></section>
  }

  if (isError) {
    return (
      <section className="parent-practice parent-practice--error" role="alert">
        <AlertCircle aria-hidden="true" />
        <div><strong>Practice summary is unavailable</strong><p>No progress was guessed or replaced with sample data.</p></div>
        <button type="button" onClick={() => refetch()}>Try again</button>
      </section>
    )
  }

  const summary = formatInteractiveSummary(data?.data)
  if (summary.empty) {
    return (
      <section className="parent-practice parent-practice--empty">
        <span className="parent-practice__hero"><Sparkles aria-hidden="true" /></span>
        <div><span className="parent-practice__eyebrow">Play & Practice</span><h2>No interactive sessions yet</h2><p>{summary.recommendation}</p></div>
        <Link to="/play">Explore activities</Link>
      </section>
    )
  }

  return (
    <section className="parent-practice" aria-labelledby="interactive-practice-title">
      <div className="parent-practice__heading">
        <div><span className="parent-practice__eyebrow">Private weekly summary</span><h2 id="interactive-practice-title">Play & Practice</h2></div>
        <span><Sparkles aria-hidden="true" /> {summary.mostPractisedLabel}</span>
      </div>
      <div className="parent-practice__stats">
        <div><Sparkles aria-hidden="true" /><strong>{summary.sessions}</strong><span>sessions this week</span></div>
        <div><MessageCircle aria-hidden="true" /><strong>{summary.turns}</strong><span>communication turns</span></div>
        <div><HandHeart aria-hidden="true" /><strong>{summary.independentPercentage}%</strong><span>independent turns</span></div>
      </div>
      <div className="parent-practice__trend">
        <div className="parent-practice__trend-title"><TrendingUp aria-hidden="true" /><span><strong>Independence trend</strong><small>Only days with a completed activity appear</small></span></div>
        <div className="parent-practice__bars">
          {summary.trend.map((point) => (
            <div key={point.date} className="parent-practice__bar">
              <span className="parent-practice__bar-value">{point.independentPercentage}%</span>
              <span className="parent-practice__bar-track" aria-label={`${point.date}: ${point.independentPercentage}% independent`}><i style={{ height: `${Math.max(6, point.independentPercentage)}%` }} /></span>
              <time dateTime={point.date}>{new Date(`${point.date}T00:00:00`).toLocaleDateString(undefined, { weekday: 'short' })}</time>
            </div>
          ))}
        </div>
      </div>
      <div className="parent-practice__recommendation"><HandHeart aria-hidden="true" /><div><strong>Try next</strong><p>{summary.recommendation}</p></div></div>
    </section>
  )
}
