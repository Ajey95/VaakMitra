import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import SensorySettingsPanel from '../components/interactive/SensorySettingsPanel'
import '../components/interactive/play.css'

export default function InteractionSettingsPage() {
  const navigate = useNavigate()
  return (
    <main className="interactive-experience comfort-page">
      <button className="interactive-control comfort-page__back" type="button" onClick={() => navigate('/play')}><ArrowLeft aria-hidden="true" /> Back to activities</button>
      <SensorySettingsPanel onDone={() => navigate('/play')} />
    </main>
  )
}
