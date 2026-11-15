const COPY = {
  success: { title: 'You did it!', detail: 'That was a brave communication try.' },
  support: { title: 'Let us try together', detail: 'A hint is ready whenever you want it.' },
  listening: { title: 'I am listening', detail: 'Take your time. There is no hurry.' },
  paused: { title: 'Activity paused', detail: 'The activity will wait for you.' },
  error: { title: 'We can use another way', detail: 'Choose a picture or ask a grown-up for help.' },
}

export default function ChildFeedback({ kind, title, detail }) {
  const message = COPY[kind] || {}
  return (
    <div className={`child-feedback child-feedback--${kind || 'neutral'}`} role="status" aria-live="polite" aria-atomic="true">
      <strong>{title || message.title}</strong>
      {(detail || message.detail) ? <span>{detail || message.detail}</span> : null}
    </div>
  )
}
