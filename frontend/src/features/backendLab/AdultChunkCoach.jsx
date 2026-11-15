/** DEC-023/DCH-003: adult visual rehearsal only; this component never receives audio. */
export default function AdultChunkCoach({ coach, localVoice, speaking, onSelect, onAdvance, onReset, onSpeak, onGoToRecording }) {
  if (coach.phase === 'idle') return null
  const selected = coach.chunks[coach.focusIndex] ?? coach.chunks[0]
  return <div className="lab-live-result" aria-label="Adult visual chunk coach">
    <strong className="lab-source">ADULT ENGINEERING · VISUAL CHUNK REHEARSAL</strong>
    <p className="lab-hint">These are written chunks, not verified syllables or a pronunciation diagnosis. No chunk is scored or uploaded.</p>
    {coach.phase !== 'break' && <>
      <p className="lab-hint">Coached cycle {coach.cycles + 1} of 2</p>
      <div className="lab-actions" aria-label="Written word chunks">
        {coach.chunks.map((chunk, index) => <button key={`${index}-${chunk}`} className={index === coach.focusIndex ? 'lab-primary' : 'lab-secondary'}
          type="button" disabled={coach.phase !== 'focus'} onClick={() => onSelect(index)}
          aria-label={`Focus chunk ${index + 1}: ${chunk}`} aria-pressed={index === coach.focusIndex}>{chunk}</button>)}
      </div>
    </>}
    {coach.phase === 'focus' && <>
      <p>{coach.basis === 'unvalidated_asr_text_difference'
        ? `Focus suggestion: ${coach.focusIndex === 0 ? 'starting' : coach.focusIndex === coach.chunks.length - 1 ? 'ending' : 'middle'} written chunk · unvalidated ASR text hypothesis.`
        : 'Focus is a manually selected visual chunk; no sound error was detected.'}</p>
      <p>Look at <strong>{selected}</strong>, say this part at a comfortable pace, then continue.</p>
      <div className="lab-actions">
        <button className="lab-secondary" type="button" disabled={!localVoice || speaking} onClick={() => onSpeak(selected)}>Hear selected chunk</button>
        <button className="lab-primary" type="button" onClick={onAdvance}>I tried this chunk</button>
      </div>
    </>}
    {coach.phase === 'blend' && <>
      <p>Blend the chunks: <strong>{coach.chunks.join(' + ')}</strong> → <strong>{coach.targetWord}</strong>.</p>
      <div className="lab-actions">
        <button className="lab-secondary" type="button" disabled={!localVoice || speaking} onClick={() => onSpeak(coach.targetWord)}>Hear whole word</button>
        <button className="lab-primary" type="button" onClick={onAdvance}>I blended the word</button>
      </div>
    </>}
    {coach.phase === 'whole_again' && <>
      <p>Now try the whole word again: <strong>{coach.targetWord}</strong>. Only the whole-word adult diagnostic will run.</p>
      <button className="lab-primary" type="button" onClick={onGoToRecording}>Go to whole-word recording</button>
    </>}
    {coach.phase === 'break' && <>
      <p>Time for a break. Two coached cycles are complete; no correctness claim was made.</p>
      <button className="lab-secondary" type="button" onClick={onReset}>Reset rehearsal</button>
    </>}
    {!localVoice && coach.phase !== 'break' && <p className="lab-hint">No locally installed Tamil voice was found. Continue with text-only practice.</p>}
  </div>
}
