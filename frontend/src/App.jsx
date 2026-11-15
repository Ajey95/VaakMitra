import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { useSettingsStore } from './store/settingsStore'
import { useInteractionSettingsStore } from './store/interactionSettingsStore'
import { authAPI } from './services/api'

const LandingPage = lazy(() => import('./pages/LandingPage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const AdminLoginPage = lazy(() => import('./pages/AdminLoginPage'))
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'))
const VerifyOtpPage = lazy(() => import('./pages/VerifyOtpPage'))
const TherapyPage = lazy(() => import('./pages/TherapyPage'))
const UserDashboard = lazy(() => import('./pages/UserDashboard'))
const TrainingPage = lazy(() => import('./pages/TrainingPage'))
const AssessmentPage = lazy(() => import('./pages/AssessmentPage'))
const LetterLearningPage = lazy(() => import('./pages/LetterLearningPage'))
const VideosPage = lazy(() => import('./pages/VideosPage'))
const SpeechAnalysisPage = lazy(() => import('./pages/SpeechAnalysisPage'))
const TongueTrackingPage = lazy(() => import('./pages/TongueTrackingPage'))
const GamesPage = lazy(() => import('./pages/GamesPage'))
const ProgressPage = lazy(() => import('./pages/ProgressPage'))
const ReportsPage = lazy(() => import('./pages/ReportsPage'))
const AchievementsPage = lazy(() => import('./pages/AchievementsPage'))
const RewardsPage = lazy(() => import('./pages/RewardsPage'))
const CalendarPage = lazy(() => import('./pages/CalendarPage'))
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'))
const AppointmentsPage = lazy(() => import('./pages/AppointmentsPage'))
const ParentDashboard = lazy(() => import('./pages/ParentDashboard'))
const TherapistDashboard = lazy(() => import('./pages/TherapistDashboard'))
const ProfilePage = lazy(() => import('./pages/ProfilePage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const HelpPage = lazy(() => import('./pages/HelpPage'))
const FeedbackPage = lazy(() => import('./pages/FeedbackPage'))
const AboutPage = lazy(() => import('./pages/AboutPage'))
const InteractiveHomePage = lazy(() => import('./pages/InteractiveHomePage'))
const InteractionSettingsPage = lazy(() => import('./pages/InteractionSettingsPage'))
const BreathBalloonPage = lazy(() => import('./pages/BreathBalloonPage'))
const RiverRescuePage = lazy(() => import('./pages/RiverRescuePage'))
const MouthMirrorPage = lazy(() => import('./pages/MouthMirrorPage'))
const PippinPage = lazy(() => import('./pages/PippinPage'))
const TalkTogetherPage = lazy(() => import('./pages/TalkTogetherPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const NotFound = lazy(() => import('./pages/NotFound'))
const BackendLabPage = import.meta.env.DEV ? lazy(() => import('./pages/BackendLabPage')) : null

function App() {
  const initTheme = useSettingsStore((s) => s.initTheme)
  const { authReady, setUser, markAuthReady } = useAuthStore()
  const initializeInteraction = useInteractionSettingsStore((state) => state.initialize)
  const user = useAuthStore((state) => state.user)

  // Re-apply the persisted theme to <html> on first paint
  useEffect(() => {
    initTheme()
  }, [initTheme])

  useEffect(() => {
    let active = true
    authAPI.getMe()
      .then(({ data }) => active && setUser(data))
      .catch(() => active && markAuthReady())
    return () => { active = false }
  }, [markAuthReady, setUser])

  useEffect(() => {
    if (authReady && user) initializeInteraction({ age: user.child_age })
  }, [authReady, initializeInteraction, user])

  if (!authReady) {
    return <div className="app-loading" aria-live="polite">Loading SpeakEasy...</div>
  }

  // Authenticated pages that all share the DashboardLayout shell
  const protectedRoutes = [
    { path: '/dashboard', element: <UserDashboard /> },
    { path: '/training', element: <TrainingPage /> },
    { path: '/assessment', element: <AssessmentPage /> },
    { path: '/letter-learning', element: <LetterLearningPage /> },
    { path: '/videos', element: <VideosPage /> },
    { path: '/speech-analysis', element: <SpeechAnalysisPage /> },
    { path: '/tongue-tracking', element: <TongueTrackingPage /> },
    { path: '/games', element: <GamesPage /> },
    { path: '/progress', element: <ProgressPage /> },
    { path: '/reports', element: <ReportsPage /> },
    { path: '/achievements', element: <AchievementsPage /> },
    { path: '/rewards', element: <RewardsPage /> },
    { path: '/calendar', element: <CalendarPage /> },
    { path: '/notifications', element: <NotificationsPage /> },
    { path: '/appointments', element: <AppointmentsPage /> },
    { path: '/parent', element: <ParentDashboard /> },
    { path: '/therapist', element: <TherapistDashboard /> },
    { path: '/profile', element: <ProfilePage /> },
    { path: '/settings', element: <SettingsPage /> },
    { path: '/help', element: <HelpPage /> },
    { path: '/feedback', element: <FeedbackPage /> },
    { path: '/about', element: <AboutPage /> },
    { path: '/play', element: <InteractiveHomePage /> },
    { path: '/play/settings', element: <InteractionSettingsPage /> },
    { path: '/play/arcade/breath-balloon', element: <BreathBalloonPage /> },
    { path: '/play/quest/river-rescue', element: <RiverRescuePage /> },
    { path: '/play/mouth-mirror', element: <MouthMirrorPage /> },
    { path: '/play/pippin', element: <PippinPage /> },
    { path: '/play/together', element: <TalkTogetherPage /> },
  ]

  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Suspense fallback={<div className="app-loading" aria-live="polite">Loading page...</div>}>
        <Routes>
        {/* Public */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/admin-login" element={<AdminLoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/verify-otp" element={<VerifyOtpPage />} />
        {import.meta.env.DEV && <Route path="/dev/backend-lab" element={<BackendLabPage />} />}

        {/* Therapy session (dynamic) */}
        <Route
          path="/therapy/:lessonId"
          element={
            <ProtectedRoute>
              <TherapyPage />
            </ProtectedRoute>
          }
        />

        {/* Authenticated app pages */}
        {protectedRoutes.map(({ path, element }) => (
          <Route
            key={path}
            path={path}
            element={<ProtectedRoute>{element}</ProtectedRoute>}
          />
        ))}

        {/* Admin — restricted to the admin role */}
        <Route
          path="/admin"
          element={
            <RoleRoute allow={['admin']}>
              <AdminPage />
            </RoleRoute>
          }
        />

        <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

// Protected route for authenticated users
function ProtectedRoute({ children }) {
  const { user, isAuthenticated } = useAuthStore()

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }

  return children
}

// Role-gated route. `allow` is a list of roles permitted to view the page.
// Note: the backend currently defines only "user" (default) and "admin" roles,
// so parent/therapist hubs are intentionally open to any authenticated user.
function RoleRoute({ children, allow }) {
  const { user, isAuthenticated } = useAuthStore()

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />
  }
  if (allow && !allow.includes(user.role)) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}

export default App
