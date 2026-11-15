import { useCallback, useEffect, useState } from 'react'
import { CalendarClock, CalendarCheck, Plus, RefreshCw, XCircle, Stethoscope } from 'lucide-react'
import toast from 'react-hot-toast'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, StatCard, SectionTitle, Badge } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import { appointmentsAPI } from '../services/api'

const formatDate = (value) => value
  ? new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  : 'Not scheduled'

const statusCopy = {
  therapist_unassigned: 'No therapist assigned',
  schedule_unestablished: 'Schedule a therapist checkup',
  not_due: 'Next checkup',
  due: 'Checkup due',
  overdue: 'Checkup overdue',
}

export default function AppointmentsPage() {
  const user = useAuthStore((state) => state.user)
  const isTherapist = user?.role === 'therapist'
  const isCaregiver = user?.role === 'user'
  const [appointments, setAppointments] = useState([])
  const [therapists, setTherapists] = useState([])
  const [checkup, setCheckup] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [kind, setKind] = useState('checkup')
  const [editing, setEditing] = useState(null)
  const [scheduledAt, setScheduledAt] = useState('')
  const [mode, setMode] = useState('online')
  const [therapistId, setTherapistId] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [appointmentResponse, therapistResponse, checkupResponse] = await Promise.all([
        appointmentsAPI.list({ limit: 100 }),
        isCaregiver ? appointmentsAPI.therapists() : Promise.resolve({ data: [] }),
        isCaregiver ? appointmentsAPI.checkupStatus() : Promise.resolve({ data: null }),
      ])
      setAppointments(appointmentResponse.data?.items || [])
      setTherapists(therapistResponse.data || [])
      setCheckup(checkupResponse.data)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Appointments are unavailable. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [isCaregiver])

  useEffect(() => { load() }, [load])

  const openForm = (nextKind = 'checkup', appointment = null) => {
    setKind(nextKind)
    setEditing(appointment)
    setScheduledAt('')
    setMode(appointment?.mode || 'online')
    setTherapistId(appointment?.therapist_id || therapists[0]?._id || '')
    setFormOpen(true)
  }

  const submit = async (event) => {
    event.preventDefault()
    if (!scheduledAt) return
    setSaving(true)
    try {
      const at = new Date(scheduledAt).toISOString()
      if (editing) await appointmentsAPI.reschedule(editing.id || editing._id, { scheduled_at: at })
      else if (kind === 'checkup') await appointmentsAPI.bookCheckup({ scheduled_at: at, mode })
      else await appointmentsAPI.book({ therapist_id: therapistId, scheduled_at: at, mode })
      setFormOpen(false)
      toast.success(editing ? 'Reschedule requested' : 'Appointment request sent')
      await load()
    } catch (requestError) {
      toast.error(requestError.response?.data?.detail || 'Could not save the appointment')
    } finally {
      setSaving(false)
    }
  }

  const changeStatus = async (appointment, status) => {
    try {
      if (status === 'cancelled') await appointmentsAPI.cancel(appointment.id || appointment._id)
      else await appointmentsAPI.updateStatus(appointment.id || appointment._id, { status })
      toast.success(`Appointment ${status}`)
      await load()
    } catch (requestError) {
      toast.error(requestError.response?.data?.detail || 'Could not update the appointment')
    }
  }

  const upcoming = appointments.filter((item) => ['pending', 'confirmed'].includes(item.status))
  const history = appointments.filter((item) => !['pending', 'confirmed'].includes(item.status))
  const checkupPending = checkup?.appointment?.status === 'pending'
  const checkupScheduled = checkup?.appointment?.status === 'confirmed'

  return (
    <DashboardLayout title="Appointments" subtitle="Therapist sessions and checkups" icon={CalendarClock}
      actions={isCaregiver && <button type="button" onClick={() => openForm('ordinary')}
        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm bg-white text-primary-600 shadow-md">
        <Plus className="w-4 h-4" /> Book appointment
      </button>}>
      {loading ? <p role="status" className="py-10 text-neutral-500">Loading appointments…</p> : error ? (
        <Card className="p-6" role="alert"><p>{error}</p><button type="button" onClick={load} className="mt-3 text-primary-600">Try again</button></Card>
      ) : <div className="space-y-7">
        {isCaregiver && <Card className="p-6" role="status">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-primary-600">Every 14 days</p>
              <h2 className="mt-1 text-xl font-bold text-neutral-900 dark:text-white">{statusCopy[checkup?.state] || 'Checkup status unavailable'}</h2>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-300">
                {checkup?.due_at ? `Due ${formatDate(checkup.due_at)}.` : 'A due date will appear after assignment or a completed checkup.'}
                {' '}Practice remains available.
              </p>
              {checkupPending && <p className="mt-2 text-sm font-semibold text-primary-600">Request pending · {formatDate(checkup.appointment.scheduled_at)}</p>}
              {checkupScheduled && <p className="mt-2 text-sm font-semibold text-accent-600">Scheduled · {formatDate(checkup.appointment.scheduled_at)}</p>}
            </div>
            {!checkup?.appointment && checkup?.state !== 'therapist_unassigned' &&
              <button type="button" onClick={() => openForm('checkup')}
                className="rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary-700">
                Request checkup
              </button>}
          </div>
        </Card>}

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
          <StatCard icon={CalendarClock} title="Upcoming" value={upcoming.length} color="primary" />
          <StatCard icon={CalendarCheck} title="Completed" value={history.filter((item) => item.status === 'completed').length} color="accent" />
          <StatCard icon={Stethoscope} title="Therapists" value={isCaregiver ? therapists.length : 1} color="secondary" />
        </div>

        <section aria-label="Upcoming appointments">
          <SectionTitle title="Upcoming sessions" subtitle="Requests and confirmed visits" icon={CalendarClock} />
          {upcoming.length === 0 ? <Card className="p-6"><p className="text-sm text-neutral-500">No upcoming appointments.</p></Card> :
            <div className="grid gap-4 sm:grid-cols-2">{upcoming.map((item) => <Card key={item.id || item._id} className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div><h3 className="font-bold text-neutral-900 dark:text-white">{item.therapist_name || 'Assigned therapist'}</h3>
                  <p className="text-sm text-neutral-500">{item.kind === 'checkup' ? '14-day checkup' : 'Therapist session'}</p></div>
                <Badge color={item.status === 'confirmed' ? 'accent' : 'primary'}>{item.status}</Badge>
              </div>
              <p className="mt-4 text-sm text-neutral-700 dark:text-neutral-200">{formatDate(item.scheduled_at)} · {item.mode === 'in_person' ? 'In person' : 'Online'}</p>
              <div className="mt-4 flex flex-wrap gap-3 text-sm">
                {isCaregiver && <button type="button" onClick={() => openForm(item.kind, item)} className="inline-flex items-center gap-1 text-primary-600"><RefreshCw className="h-4 w-4" /> Reschedule</button>}
                {isTherapist && item.status === 'pending' && <button type="button" onClick={() => changeStatus(item, 'confirmed')} className="text-primary-600">Confirm</button>}
                {isTherapist && item.status === 'confirmed' && <button type="button" onClick={() => changeStatus(item, 'completed')} className="text-accent-600">Mark completed</button>}
                {isTherapist && item.status === 'confirmed' && <button type="button" onClick={() => changeStatus(item, 'no_show')} className="text-coral-600">Mark no-show</button>}
                <button type="button" onClick={() => changeStatus(item, 'cancelled')} className="inline-flex items-center gap-1 text-coral-600"><XCircle className="h-4 w-4" /> Cancel</button>
              </div>
            </Card>)}</div>}
        </section>

        <section aria-label="Past appointments"><SectionTitle title="Past appointments" subtitle="Confirmed history only" icon={CalendarCheck} />
          {history.length === 0 ? <Card className="p-6"><p className="text-sm text-neutral-500">No past appointments.</p></Card> :
            <Card className="overflow-x-auto p-4"><table className="w-full text-left text-sm"><thead><tr><th className="p-2">Therapist</th><th className="p-2">Date</th><th className="p-2">Type</th><th className="p-2">Status</th></tr></thead>
              <tbody>{history.map((item) => <tr key={item.id || item._id} className="border-t border-neutral-100 dark:border-neutral-800"><td className="p-2">{item.therapist_name || 'Therapist'}</td><td className="p-2">{formatDate(item.scheduled_at)}</td><td className="p-2">{item.kind === 'checkup' ? 'Checkup' : 'Session'}</td><td className="p-2">{item.status}</td></tr>)}</tbody></table></Card>}
        </section>

        {isCaregiver && <section aria-label="Available therapists"><SectionTitle title="Available therapists" subtitle="Registered providers" icon={Stethoscope} />
          {therapists.length === 0 ? <Card className="p-6"><p className="text-sm text-neutral-500">No therapist profiles are available.</p></Card> :
            <div className="grid gap-3 sm:grid-cols-2">{therapists.map((therapist) => <Card key={therapist._id || therapist.id} className="p-4"><p className="font-semibold">{therapist.full_name}</p><p className="text-xs text-neutral-500">Registration does not imply clinical credential verification.</p></Card>)}</div>}
        </section>}
      </div>}

      {formOpen && <div className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/60 p-4" role="presentation">
        <div role="dialog" aria-modal="true" aria-label={editing ? 'Reschedule appointment' : kind === 'checkup' ? 'Request checkup' : 'Book appointment'}
          className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl dark:bg-neutral-900">
          <h2 className="text-lg font-bold text-neutral-900 dark:text-white">{editing ? 'Reschedule appointment' : kind === 'checkup' ? 'Request checkup' : 'Book appointment'}</h2>
          <form onSubmit={submit} className="mt-5 space-y-4">
            {kind === 'ordinary' && !editing && <label className="block text-sm font-medium">Therapist
              <select value={therapistId} onChange={(event) => setTherapistId(event.target.value)} required className="mt-1 w-full rounded-xl border p-2 dark:bg-neutral-800">
                <option value="">Select a therapist</option>{therapists.map((therapist) => <option key={therapist._id || therapist.id} value={therapist._id || therapist.id}>{therapist.full_name}</option>)}
              </select></label>}
            <label className="block text-sm font-medium">Date and time
              <input type="datetime-local" value={scheduledAt} onChange={(event) => setScheduledAt(event.target.value)} required
                className="mt-1 w-full rounded-xl border p-2 dark:bg-neutral-800" />
            </label>
            {!editing && <label className="block text-sm font-medium">Mode
              <select value={mode} onChange={(event) => setMode(event.target.value)} className="mt-1 w-full rounded-xl border p-2 dark:bg-neutral-800"><option value="online">Online</option><option value="in_person">In person</option></select>
            </label>}
            {kind === 'checkup' && <p className="text-sm text-neutral-500">The request goes only to the assigned therapist. It is not a confirmed visit.</p>}
            <div className="flex justify-end gap-3"><button type="button" onClick={() => setFormOpen(false)} className="rounded-xl px-4 py-2 text-sm">Close</button>
              <button type="submit" disabled={saving || (kind === 'ordinary' && !therapistId)} className="rounded-xl bg-primary-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? 'Sending…' : editing ? 'Save request' : 'Send request'}</button></div>
          </form>
        </div>
      </div>}
    </DashboardLayout>
  )
}
