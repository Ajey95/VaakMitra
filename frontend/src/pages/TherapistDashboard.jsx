import { useCallback, useEffect, useState } from 'react'
import { ClipboardCheck, Stethoscope, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle } from '../components/ui'
import { therapistAPI, governanceAPI } from '../services/api'

export default function TherapistDashboard() {
  const [children, setChildren] = useState([])
  const [batches, setBatches] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [assignEmail, setAssignEmail] = useState('')
  const [observedHash, setObservedHash] = useState('')
  const [qualityScore, setQualityScore] = useState('')
  const [acknowledged, setAcknowledged] = useState(false)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [childResponse, batchResponse] = await Promise.all([
        therapistAPI.getChildren(), governanceAPI.batches(),
      ])
      setChildren(childResponse.data?.children || [])
      setBatches(batchResponse.data?.items || [])
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Therapist data is unavailable.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const assign = async (event) => {
    event.preventDefault()
    if (!assignEmail.trim()) return
    setSaving(true)
    try {
      await therapistAPI.assignChild(assignEmail.trim())
      setAssignEmail('')
      toast.success('Child assigned')
      await load()
    } catch (requestError) {
      toast.error(requestError.response?.data?.detail || 'Could not assign child')
    } finally {
      setSaving(false)
    }
  }

  const openBatch = async (id) => {
    try {
      const response = await governanceAPI.batch(id)
      setSelected(response.data)
      setObservedHash('')
      setQualityScore('')
      setAcknowledged(false)
    } catch (requestError) {
      toast.error(requestError.response?.data?.detail || 'Could not open review batch')
    }
  }

  const decide = async (item, decision) => {
    const batch = selected?.batch
    if (!batch || !acknowledged) return
    const expected = batch.kind === 'clinical' ? item.content_sha256 : item.audio_sha256
    if (observedHash.trim().toLowerCase() !== expected) {
      toast.error('The observed hash must match this exact item')
      return
    }
    const payload = {
      item_id: item.item_id, observed_sha256: observedHash.trim().toLowerCase(), decision,
    }
    if (batch.kind === 'reference' && decision === 'approved') {
      const score = Number(qualityScore)
      if (qualityScore === '' || !Number.isFinite(score) || score < 0 || score > 1) {
        toast.error('Enter a quality score from 0 to 1')
        return
      }
      payload.capture_valid = true
      payload.quality_score = score
    }
    setSaving(true)
    try {
      await governanceAPI.review(batch.id || batch._id, payload)
      toast.success('Human review decision recorded')
      await Promise.all([openBatch(batch.id || batch._id), load()])
    } catch (requestError) {
      toast.error(requestError.response?.data?.detail || 'Could not record review')
    } finally {
      setSaving(false)
    }
  }

  const reviewed = new Set(selected?.decisions?.map((row) => row.item_id) || [])
  const remaining = selected?.batch?.items?.filter((item) => !reviewed.has(item.item_id)) || []
  const item = remaining[0]
  const expectedHash = item && (selected.batch.kind === 'clinical' ? item.content_sha256 : item.audio_sha256)

  return <DashboardLayout title="Therapist Dashboard" subtitle="Assigned children and human review" icon={Stethoscope}>
    {loading ? <p role="status" className="py-10 text-neutral-500">Loading therapist workspace…</p>
      : error ? <Card className="p-6" role="alert"><p>{error}</p><button type="button" onClick={load} className="mt-3 text-primary-600">Try again</button></Card>
        : <div className="space-y-7">
          <Card className="p-6">
            <SectionTitle title="Assigned children" subtitle="Only current assignments appear here" icon={Users} />
            {children.length === 0 ? <p className="text-sm text-neutral-500">No children are assigned.</p>
              : <ul className="grid gap-3 sm:grid-cols-2">{children.map((child) => <li key={child.id} className="rounded-xl border border-neutral-100 p-4 dark:border-neutral-800">
                <p className="font-semibold text-neutral-900 dark:text-white">{child.child_name || child.full_name || 'Child profile'}</p>
                <p className="mt-1 text-xs text-neutral-500">No unvalidated accuracy or phoneme claim is shown.</p>
              </li>)}</ul>}
            <form onSubmit={assign} className="mt-5 flex flex-wrap gap-2">
              <label className="sr-only" htmlFor="assign-child-email">Child account email</label>
              <input id="assign-child-email" type="email" value={assignEmail} onChange={(event) => setAssignEmail(event.target.value)}
                placeholder="Child account email" className="min-w-0 flex-1 rounded-xl border px-3 py-2 dark:bg-neutral-800" />
              <button type="submit" disabled={saving} className="rounded-xl bg-primary-600 px-4 py-2 text-sm font-semibold text-white">Assign</button>
            </form>
            <Link to="/appointments" className="mt-4 inline-block text-sm font-semibold text-primary-600">View checkup requests</Link>
          </Card>

          <Card className="p-6">
            <SectionTitle title="Human review queue" subtitle="Credential-verified scope only; no approval is automatic" icon={ClipboardCheck} />
            {batches.length === 0 ? <p className="text-sm text-neutral-500">No review batches are available for your verified scope.</p> :
              <ul className="space-y-3">{batches.map((batch) => <li key={batch.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-neutral-100 p-4 dark:border-neutral-800">
                <div><p className="font-semibold capitalize">{batch.kind} review</p><p className="text-sm text-neutral-500">Reviewed {batch.reviewed_count} of {batch.item_count}</p>
                  <p className="mt-1 break-all font-mono text-xs text-neutral-400">Manifest {batch.manifest_sha256}</p></div>
                <button type="button" onClick={() => openBatch(batch.id)} className="rounded-xl border border-primary-200 px-3 py-2 text-sm font-semibold text-primary-600">Open {batch.kind} review</button>
              </li>)}</ul>}
          </Card>

          {selected && <Card className="p-6" role="region" aria-label="Review batch detail">
            <div className="flex items-start justify-between gap-3"><SectionTitle title="Exact-item review" subtitle="Review the source and hash outside this app before deciding" icon={ClipboardCheck} />
              <button type="button" onClick={() => setSelected(null)} className="text-sm text-neutral-500">Close</button></div>
            {!item ? <p className="text-sm text-accent-600">All items have decisions. An administrator must export and independently verify the batch; this is not a clinical release.</p> : <div className="space-y-4">
              <p className="font-semibold">{item.item_id}{item.word_id ? ` · ${item.word_id}` : ''}</p>
              <p className="break-all font-mono text-xs text-neutral-500">Expected SHA-256: {expectedHash}</p>
              <p className="text-sm text-neutral-500">Source audio or content is reviewed outside this app. No child audio is served here.</p>
              <label className="block text-sm font-medium">Observed SHA-256
                <input value={observedHash} onChange={(event) => setObservedHash(event.target.value)} autoComplete="off"
                  className="mt-1 w-full rounded-xl border px-3 py-2 font-mono text-xs dark:bg-neutral-800" />
              </label>
              {selected.batch.kind === 'reference' && <label className="block text-sm font-medium">Quality score
                <input type="number" step="0.01" min="0" max="1" value={qualityScore} onChange={(event) => setQualityScore(event.target.value)}
                  className="mt-1 w-full rounded-xl border px-3 py-2 dark:bg-neutral-800" />
              </label>}
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />I reviewed the source outside the app</label>
              <div className="flex gap-3"><button type="button" disabled={saving || !acknowledged} onClick={() => decide(item, 'approved')}
                className="rounded-xl bg-accent-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">Approve item</button>
                <button type="button" disabled={saving || !acknowledged} onClick={() => decide(item, 'rejected')}
                  className="rounded-xl border border-coral-200 px-4 py-2 text-sm font-semibold text-coral-600 disabled:opacity-50">Reject item</button></div>
            </div>}
          </Card>}
        </div>}
  </DashboardLayout>
}
