import { CalendarClock, Heart, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import { appointmentsAPI, governanceAPI } from '../services/api'
import InteractivePracticeSummary from '../components/parent/InteractivePracticeSummary'
import '../components/parent/parent-practice.css'

const statusLabel = {
  therapist_unassigned: 'No therapist assigned',
  schedule_unestablished: 'Schedule a therapist checkup',
  not_due: 'Next therapist checkup',
  due: 'Therapist checkup due',
  overdue: 'Therapist checkup overdue',
}

export default function ParentDashboard() {
  const user = useAuthStore((state) => state.user)
  const checkup = useQuery({
    queryKey: ['checkupStatus', user?._id],
    queryFn: () => appointmentsAPI.checkupStatus(),
    enabled: Boolean(user),
    staleTime: 30_000,
  })
  const consents = useQuery({
    queryKey: ['consentReceipts', user?._id],
    queryFn: () => governanceAPI.myConsents(),
    enabled: Boolean(user),
    staleTime: 30_000,
  })
  const state = checkup.data?.data
  const consentItems = consents.data?.data?.items || []

  return <DashboardLayout title="Parent Dashboard" subtitle="Private practice and therapist contact" icon={Heart}>
    <div className="space-y-6">
      <div className="rounded-3xl bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 p-6 text-white shadow-md sm:p-8">
        <h1 className="text-2xl font-bold sm:text-3xl">{user?.child_name || 'Your child'}&apos;s practice</h1>
        <p className="mt-2 max-w-2xl text-sm text-white/80">Short, supported activities can continue while a checkup is due. This app does not replace the therapist.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <SectionTitle title="Therapist checkup" subtitle="Every 14 days" icon={CalendarClock} />
          {checkup.isPending ? <p role="status" className="text-sm text-neutral-500">Loading checkup status…</p>
            : checkup.isError ? <p role="alert" className="text-sm text-coral-600">Checkup status is unavailable. No visit has been inferred.</p>
              : <>
                <p className="text-lg font-semibold text-neutral-900 dark:text-white">{statusLabel[state?.state] || 'Checkup status unavailable'}</p>
                <p className="mt-2 text-sm text-neutral-500">{state?.due_at ? `Due ${new Date(state.due_at).toLocaleString()}. ` : ''}Practice remains available.</p>
                {state?.appointment && <p className="mt-2 text-sm text-primary-600">{state.appointment.status === 'pending' ? 'Request pending' : 'Visit scheduled'} · {new Date(state.appointment.scheduled_at).toLocaleString()}</p>}
                <Link to="/appointments" className="mt-4 inline-flex rounded-xl bg-primary-600 px-4 py-2.5 text-sm font-semibold text-white">Manage checkup</Link>
              </>}
        </Card>
        <Card className="p-6">
          <SectionTitle title="Consent evidence" subtitle="Human verification only" icon={ShieldCheck} />
          {consents.isPending ? <p role="status" className="text-sm text-neutral-500">Loading consent status…</p>
            : consents.isError ? <p role="alert" className="text-sm text-coral-600">Consent status is unavailable.</p>
              : consentItems.length === 0 ? <p className="text-sm text-neutral-500">No verified research or child-validation consent is recorded. Practice does not create research consent.</p>
                : <ul className="space-y-2">{consentItems.map((item) => <li key={item.id} className="text-sm text-neutral-700 dark:text-neutral-200">{item.protocol_id} · {item.status.replaceAll('_', ' ')}</li>)}</ul>}
        </Card>
      </div>
      <InteractivePracticeSummary />
    </div>
  </DashboardLayout>
}
