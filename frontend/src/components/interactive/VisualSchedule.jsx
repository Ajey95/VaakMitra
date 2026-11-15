import { Check, Circle, Play } from 'lucide-react'

export default function VisualSchedule({ steps, activeIndex = 0 }) {
  return (
    <ol className="visual-schedule" aria-label="Activity steps">
      {steps.map((step, index) => {
        const complete = index < activeIndex
        const active = index === activeIndex
        return (
          <li key={step.id || step.label} className={complete ? 'is-complete' : active ? 'is-active' : ''} aria-current={active ? 'step' : undefined}>
            <span className="visual-schedule__dot" aria-hidden="true">
              {complete ? <Check /> : active ? <Play /> : <Circle />}
            </span>
            <span>{step.shortLabel || step.label}</span>
          </li>
        )
      })}
    </ol>
  )
}
