import axios from 'axios'
import { useAuthStore } from '../store/authStore'
import { resolveApiBaseUrl, resolveCanonicalApiBaseUrl } from './apiConfig'

const apiBaseUrl = resolveApiBaseUrl({
  isDevelopment: import.meta.env.DEV,
  configuredUrl: import.meta.env.VITE_API_BASE_URL,
})

const api = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const canonicalWordClient = axios.create({
  baseURL: resolveCanonicalApiBaseUrl({ isDevelopment: import.meta.env.DEV, configuredUrl: import.meta.env.VITE_API_BASE_URL }),
  withCredentials: true,
})

// Add response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Don't redirect if already on login/register/landing pages
      const currentPath = window.location.pathname
      const publicPaths = ['/', '/login', '/register', '/admin-login', '/forgot-password', '/verify-otp']
      
      // DEC-008: the development lab must display 401 rather than redirect away from evidence.
      if (!publicPaths.includes(currentPath) && !(import.meta.env.DEV && currentPath === '/dev/backend-lab')) {
        useAuthStore.getState().logout()
        // Use soft navigation instead of hard reload to prevent blink
        window.location.replace('/login')
      }
    }
    return Promise.reject(error)
  }
)

// Auth endpoints
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  adminLogin: (data) => api.post('/auth/admin/login', data),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  changePassword: (data) => api.post('/auth/change-password', data),
  // Password reset (OTP) + email verification + sessions
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  verifyOtp: (email, otp) => api.post('/auth/verify-otp', { email, otp }),
  resetPassword: (data) => api.post('/auth/reset-password', data),
  requestEmailVerify: () => api.post('/auth/verify-email/request'),
  confirmEmailVerify: (otp) => api.post('/auth/verify-email/confirm', { otp }),
  refresh: () => api.post('/auth/refresh'),
  getSessions: () => api.get('/auth/sessions'),
  revokeSession: (id) => api.delete(`/auth/sessions/${id}`),
}

// Therapy endpoints
export const therapyAPI = {
  getLessons: () => api.get('/therapy/lessons'),
  getLesson: (id) => api.get(`/therapy/lessons/${id}`),
}

// Evaluation endpoints
export const evaluationAPI = {
  evaluateSpeech: (formData) => {
    return api.post('/evaluate/speech', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
}

export const storyVoiceAPI = {
  get: (lineId) => api.get(`/story-voice/${encodeURIComponent(lineId)}`, { responseType: 'blob' }),
}

// Progress endpoints
export const progressAPI = {
  saveProgress: (data) => api.post('/progress/save', data),
  getUserProgress: (userId) => api.get(`/progress/user/${userId}`),
  getProgressSummary: (userId) => api.get(`/progress/summary/${userId}`),
}

// Admin endpoints
export const adminAPI = {
  getUsers: (params) => api.get('/admin/users', { params }),
  getUserDetail: (userId) => api.get(`/admin/users/${userId}`),
  deleteUser: (userId) => api.delete(`/admin/users/${userId}`),
  getStats: () => api.get('/admin/stats'),
  exportCSV: () => api.get('/admin/export/csv', { responseType: 'blob' }),
  // Control-center (admin_ext)
  getDashboard: () => api.get('/admin/dashboard'),
  getEngagement: () => api.get('/admin/metrics/engagement'),
  getAllUsers: (params) => api.get('/admin/all-users', { params }),
  createUser: (data) => api.post('/admin/users', data),
  editUser: (id, data) => api.patch(`/admin/users/${id}/edit`, data),
  changeRole: (id, role) => api.patch(`/admin/users/${id}/role`, { role }),
  blockUser: (id) => api.post(`/admin/users/${id}/block`),
  unblockUser: (id) => api.post(`/admin/users/${id}/unblock`),
  resetUserPassword: (id, new_password) => api.post(`/admin/users/${id}/reset-password`, { new_password }),
  getAudit: (params) => api.get('/admin/audit', { params }),
  getAuditActions: () => api.get('/admin/audit/actions'),
  exportAudit: () => api.get('/admin/audit/export', { responseType: 'blob' }),
  getCollections: () => api.get('/admin/collections'),
  browseCollection: (name, params) => api.get(`/admin/collections/${name}`, { params }),
  deleteDocument: (name, id) => api.delete(`/admin/collections/${name}/${id}`),
  getSystemHealth: () => api.get('/admin/system/health'),
}

// Contact endpoint
export const contactAPI = {
  submitContact: (data) => api.post('/contact', data),
}

// Gamification endpoints (achievements + leaderboard, derived from real data)
export const gamificationAPI = {
  getAchievements: (userId) => api.get(`/achievements/${userId}`),
  getLeaderboard: (limit = 10) => api.get('/leaderboard', { params: { limit } }),
}

// Speech analytics (aggregated from stored evaluations)
export const analysisAPI = {
  getAnalysis: (userId) => api.get(`/analysis/${userId}`),
  getPhoneme: (userId, phoneme) => api.get(`/analysis/phoneme/${userId}/${phoneme}`),
  getRecommendations: (userId) => api.get(`/analysis/recommendations/${userId}`),
  getConsistency: (userId) => api.get(`/analysis/consistency/${userId}`),
  getSkillRadar: (userId) => api.get(`/analysis/skill-radar/${userId}`),
}

// Progress (extended)
export const progressExtAPI = {
  getHistory: (userId, params) => api.get(`/progress/history/${userId}`, { params }),
  getLessonDetail: (userId, lessonId) => api.get(`/progress/lesson/${userId}/${lessonId}`),
  getOverview: (userId) => api.get(`/progress/overview/${userId}`),
  export: (userId) => api.get(`/progress/export/${userId}`, { responseType: 'blob' }),
  deleteEvaluation: (id) => api.delete(`/progress/evaluation/${id}`),
}

// Therapist portal
export const therapistAPI = {
  register: (data) => api.post('/therapist/register', data),
  getChildren: () => api.get('/therapist/children'),
  getChild: (childId) => api.get(`/therapist/children/${childId}`),
  assignChild: (childEmail) => api.post('/therapist/assign', { child_email: childEmail }),
  unassignChild: (childId) => api.delete(`/therapist/children/${childId}`),
  // Clinical notes + treatment plans
  addNote: (data) => api.post('/therapist/notes', data),
  getNotes: (childId, params) => api.get(`/therapist/notes/${childId}`, { params }),
  deleteNote: (id) => api.delete(`/therapist/notes/${id}`),
  createPlan: (data) => api.post('/therapist/plans', data),
  getPlans: (childId) => api.get(`/therapist/plans/${childId}`),
  togglePlanGoal: (planId, i) => api.patch(`/therapist/plans/${planId}/goal/${i}`),
  deletePlan: (id) => api.delete(`/therapist/plans/${id}`),
}

// Parent portal
export const parentAPI = {
  getWeekly: () => api.get('/parent/weekly'),
  getChildren: () => api.get('/parent/children'),
  addChild: (data) => api.post('/parent/children', data),
  removeChild: (id) => api.delete(`/parent/children/${id}`),
  getMonthly: (childId) => api.get(`/parent/monthly/${childId}`),
  getMilestones: (childId) => api.get(`/parent/milestones/${childId}`),
}

// Notifications
export const notificationsAPI = {
  list: (params) => api.get('/notifications', { params }),
  unreadCount: () => api.get('/notifications/unread-count'),
  get: (id) => api.get(`/notifications/${id}`),
  markRead: (id) => api.patch(`/notifications/${id}/read`),
  markUnread: (id) => api.patch(`/notifications/${id}/unread`),
  markAllRead: () => api.post('/notifications/read-all'),
  remove: (id) => api.delete(`/notifications/${id}`),
  clearAll: () => api.delete('/notifications'),
  adminCreate: (data) => api.post('/notifications/admin/create', data),
  adminBroadcast: (data) => api.post('/notifications/admin/broadcast', data),
}

// Settings (server-persisted)
export const settingsAPI = {
  get: () => api.get('/settings'),
  update: (data) => api.put('/settings', data),
  reset: () => api.post('/settings/reset'),
}

// Feedback
export const feedbackAPI = {
  submit: (data) => api.post('/feedback', data),
  mine: (params) => api.get('/feedback/mine', { params }),
  summary: () => api.get('/feedback/summary'),
  adminList: (params) => api.get('/feedback/admin/all', { params }),
  adminStats: () => api.get('/feedback/admin/stats'),
  adminTriage: (id, data) => api.patch(`/feedback/admin/${id}`, data),
  adminDelete: (id) => api.delete(`/feedback/admin/${id}`),
}

// Profile (multi-tab)
export const profileAPI = {
  get: () => api.get('/profile'),
  updatePersonal: (data) => api.patch('/profile/personal', data),
  updateChild: (data) => api.patch('/profile/child', data),
  updateMedical: (data) => api.patch('/profile/medical', data),
  updatePreferences: (data) => api.patch('/profile/preferences', data),
  listEmergency: () => api.get('/profile/emergency-contacts'),
  addEmergency: (data) => api.post('/profile/emergency-contacts', data),
  deleteEmergency: (id) => api.delete(`/profile/emergency-contacts/${id}`),
  setAvatar: (avatar_url) => api.post('/profile/avatar', { avatar_url }),
}

// Appointments
export const appointmentsAPI = {
  book: (data) => api.post('/appointments', data),
  bookCheckup: (data) => api.post('/appointments/checkups', data),
  checkupStatus: () => api.get('/appointments/checkup-status'),
  list: (params) => api.get('/appointments', { params }),
  therapists: () => api.get('/appointments/available-therapists'),
  get: (id) => api.get(`/appointments/${id}`),
  reschedule: (id, data) => api.patch(`/appointments/${id}/reschedule`, data),
  updateStatus: (id, data) => api.patch(`/appointments/${id}/status`, data),
  cancel: (id) => api.delete(`/appointments/${id}`),
  adminAll: (params) => api.get('/appointments/admin/all', { params }),
}

// GOV-001..007: status and qualified-human review metadata only.
export const governanceAPI = {
  myConsents: () => api.get('/governance/consents/me'),
  batches: () => api.get('/governance/batches'),
  batch: (id) => api.get(`/governance/batches/${id}`),
  review: (id, data) => api.post(`/governance/batches/${id}/decisions`, data),
}

// Calendar
export const calendarAPI = {
  createEvent: (data) => api.post('/calendar/events', data),
  listEvents: (params) => api.get('/calendar/events', { params }),
  upcoming: (days = 7) => api.get('/calendar/upcoming', { params: { days } }),
  updateEvent: (id, data) => api.patch(`/calendar/events/${id}`, data),
  deleteEvent: (id) => api.delete(`/calendar/events/${id}`),
}

// Announcements
export const announcementsAPI = {
  list: (params) => api.get('/announcements', { params }),
  banner: () => api.get('/announcements/banner'),
  get: (id) => api.get(`/announcements/${id}`),
  adminCreate: (data) => api.post('/announcements/admin', data),
  adminAll: (params) => api.get('/announcements/admin/all', { params }),
  adminUpdate: (id, data) => api.patch(`/announcements/admin/${id}`, data),
  adminDelete: (id) => api.delete(`/announcements/admin/${id}`),
}

// Games
export const gamesAPI = {
  list: (category) => api.get('/games', { params: { category } }),
  myScores: () => api.get('/games/my-scores'),
  detail: (slug) => api.get(`/games/${slug}`),
  submitScore: (data) => api.post('/games/score', data),
  leaderboard: (slug, limit = 10) => api.get(`/games/${slug}/leaderboard`, { params: { limit } }),
  adminCreate: (data) => api.post('/games/admin', data),
  adminDelete: (slug) => api.delete(`/games/admin/${slug}`),
}

// Wallet / rewards / shop
export const walletAPI = {
  get: () => api.get('/wallet'),
  transactions: (params) => api.get('/wallet/transactions', { params }),
  dailyReward: () => api.post('/wallet/daily-reward'),
  shop: (type) => api.get('/wallet/shop', { params: { type } }),
  buy: (slug) => api.post(`/wallet/shop/${slug}/buy`),
  inventory: () => api.get('/wallet/inventory'),
  equip: (slug) => api.post(`/wallet/inventory/${slug}/equip`),
  adminAdjust: (data) => api.post('/wallet/admin/adjust', data),
}

// Assessment / quizzes
export const assessmentAPI = {
  list: (params) => api.get('/assessment', { params }),
  get: (slug) => api.get(`/assessment/${slug}`),
  submit: (data) => api.post('/assessment/submit', data),
  history: (params) => api.get('/assessment/attempts/history', { params }),
  best: () => api.get('/assessment/attempts/best'),
  create: (data) => api.post('/assessment/admin', data),
  update: (slug, data) => api.patch(`/assessment/admin/${slug}`, data),
  remove: (slug) => api.delete(`/assessment/admin/${slug}`),
}

// Videos
export const videosAPI = {
  list: (params) => api.get('/videos', { params }),
  categories: () => api.get('/videos/categories'),
  get: (slug) => api.get(`/videos/${slug}`),
  saveProgress: (slug, data) => api.post(`/videos/${slug}/progress`, data),
  adminCreate: (data) => api.post('/videos/admin', data),
  adminUpdate: (slug, data) => api.patch(`/videos/admin/${slug}`, data),
  adminDelete: (slug) => api.delete(`/videos/admin/${slug}`),
}

// Reports
export const reportsAPI = {
  meta: () => api.get('/reports/meta'),
  run: (data) => api.post('/reports/run', data),
  runFor: (userId, data) => api.post(`/reports/run/${userId}`, data),
  save: (data) => api.post('/reports/save', data),
  saved: () => api.get('/reports/saved'),
  deleteSaved: (id) => api.delete(`/reports/saved/${id}`),
  export: (data) => api.post('/reports/export', data, { responseType: 'blob' }),
}

// Social
export const socialAPI = {
  sendRequest: (email) => api.post('/social/friends/request', { email }),
  friends: () => api.get('/social/friends'),
  requests: () => api.get('/social/friends/requests'),
  accept: (id) => api.post(`/social/friends/${id}/accept`),
  removeFriend: (id) => api.delete(`/social/friends/${id}`),
  friendsLeaderboard: () => api.get('/social/leaderboard/friends'),
  globalLeaderboard: (limit = 20) => api.get('/social/leaderboard/global', { params: { limit } }),
}

// Messaging
export const messagingAPI = {
  start: (data) => api.post('/messaging/conversations', data),
  conversations: () => api.get('/messaging/conversations'),
  messages: (id, params) => api.get(`/messaging/conversations/${id}/messages`, { params }),
  send: (id, body) => api.post(`/messaging/conversations/${id}/messages`, { body }),
  unreadCount: () => api.get('/messaging/unread-count'),
  deleteConversation: (id) => api.delete(`/messaging/conversations/${id}`),
}

// Goals & challenges
export const goalsAPI = {
  create: (data) => api.post('/goals', data),
  list: () => api.get('/goals'),
  remove: (id) => api.delete(`/goals/${id}`),
  challenges: () => api.get('/goals/challenges'),
  joinChallenge: (id) => api.post(`/goals/challenges/${id}/join`),
  claimChallenge: (id) => api.post(`/goals/challenges/${id}/claim`),
  createChallenge: (data) => api.post('/goals/challenges/admin', data),
}

// Streaks
export const streaksAPI = {
  mine: () => api.get('/streaks'),
  heatmap: () => api.get('/streaks/heatmap'),
  forUser: (userId) => api.get(`/streaks/${userId}`),
}

// Enquiries
export const enquiriesAPI = {
  create: (data) => api.post('/enquiries', data),
  mine: (params) => api.get('/enquiries', { params }),
  get: (id) => api.get(`/enquiries/${id}`),
  adminAll: (params) => api.get('/enquiries/admin/all', { params }),
  adminRespond: (id, data) => api.post(`/enquiries/admin/${id}/respond`, data),
}

// Support (tickets + FAQ)
export const supportAPI = {
  createTicket: (data) => api.post('/support/tickets', data),
  myTickets: (params) => api.get('/support/tickets', { params }),
  getTicket: (id) => api.get(`/support/tickets/${id}`),
  replyTicket: (id, data) => api.post(`/support/tickets/${id}/reply`, data),
  adminTickets: (params) => api.get('/support/tickets/admin/all', { params }),
  faq: (category) => api.get('/support/faq', { params: { category } }),
  createFaq: (data) => api.post('/support/faq/admin', data),
  deleteFaq: (id) => api.delete(`/support/faq/admin/${id}`),
}

// Devices (push tokens)
export const devicesAPI = {
  register: (data) => api.post('/devices/register', data),
  list: () => api.get('/devices'),
  unregister: (id) => api.delete(`/devices/${id}`),
}

// Global search
export const searchAPI = {
  search: (q) => api.get('/search', { params: { q } }),
  suggest: (q) => api.get('/search/suggest', { params: { q } }),
}

// Wishlist & suggestions
export const wishlistAPI = {
  add: (data) => api.post('/wishlist', data),
  list: () => api.get('/wishlist'),
  remove: (id) => api.delete(`/wishlist/${id}`),
  suggest: (data) => api.post('/wishlist/suggest', data),
  suggestions: (params) => api.get('/wishlist/suggestions', { params }),
  voteSuggestion: (id) => api.post(`/wishlist/suggestions/${id}/vote`),
}

// Content / blog
export const contentAPI = {
  list: (params) => api.get('/content', { params }),
  tags: () => api.get('/content/tags'),
  get: (id) => api.get(`/content/${id}`),
  like: (id) => api.post(`/content/${id}/like`),
  adminCreate: (data) => api.post('/content/admin', data),
  adminAll: (params) => api.get('/content/admin/all', { params }),
  adminUpdate: (id, data) => api.patch(`/content/admin/${id}`, data),
  adminDelete: (id) => api.delete(`/content/admin/${id}`),
}

// Lessons (custom, admin-managed)
export const lessonsAPI = {
  listCustom: (category) => api.get('/lessons/custom', { params: { category } }),
  getCustom: (id) => api.get(`/lessons/custom/${id}`),
  categories: () => api.get('/lessons/categories'),
  create: (data) => api.post('/lessons/admin', data),
  update: (id, data) => api.patch(`/lessons/admin/${id}`, data),
  remove: (id) => api.delete(`/lessons/admin/${id}`),
  createCategory: (data) => api.post('/lessons/categories/admin', data),
  deleteCategory: (id) => api.delete(`/lessons/categories/admin/${id}`),
}

// Badges (claimable)
export const badgesAPI = {
  list: () => api.get('/badges'),
  claim: (slug) => api.post(`/badges/${slug}/claim`),
  claimed: () => api.get('/badges/claimed'),
  adminCreate: (data) => api.post('/badges/admin', data),
  adminDelete: (slug) => api.delete(`/badges/admin/${slug}`),
}

// Billing / subscriptions
export const billingAPI = {
  plans: () => api.get('/billing/plans'),
  subscription: () => api.get('/billing/subscription'),
  subscribe: (plan_slug) => api.post('/billing/subscribe', { plan_slug }),
  cancel: () => api.post('/billing/cancel'),
  invoices: (params) => api.get('/billing/invoices', { params }),
  invoice: (id) => api.get(`/billing/invoices/${id}`),
  createPlan: (data) => api.post('/billing/plans/admin', data),
  revenue: () => api.get('/billing/admin/revenue'),
}

// Referrals
export const referralsAPI = {
  myCode: () => api.get('/referrals/my-code'),
  redeem: (code) => api.post('/referrals/redeem', { code }),
  history: () => api.get('/referrals/history'),
  leaderboard: () => api.get('/referrals/leaderboard'),
}

// Uploads
export const uploadsAPI = {
  upload: (formData) => api.post('/uploads', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  list: (params) => api.get('/uploads', { params }),
  remove: (id) => api.delete(`/uploads/${id}`),
}

// Reminders
export const remindersAPI = {
  create: (data) => api.post('/reminders', data),
  list: () => api.get('/reminders'),
  update: (id, data) => api.patch(`/reminders/${id}`, data),
  remove: (id) => api.delete(`/reminders/${id}`),
  fire: (id) => api.post(`/reminders/${id}/fire`),
}

// Activity feed
export const activityAPI = {
  mine: (limit = 20) => api.get('/activity', { params: { limit } }),
  forUser: (userId, limit = 20) => api.get(`/activity/${userId}`, { params: { limit } }),
  today: () => api.get('/activity/summary/today'),
}

// Privacy-minimal aggregate reporting for child Play & Practice sessions.
export const interactiveSessionsAPI = {
  create: (data) => api.post('/interactive-sessions', data),
  summary: () => api.get('/interactive-sessions/summary'),
}

// Moderation
export const moderationAPI = {
  report: (data) => api.post('/moderation/report', data),
  queue: (params) => api.get('/moderation/queue', { params }),
  stats: () => api.get('/moderation/stats'),
  review: (id, data) => api.patch(`/moderation/${id}`, data),
}

// Privacy / GDPR
export const privacyAPI = {
  exportData: () => api.get('/privacy/export', { responseType: 'blob' }),
  requestDeletion: (reason) => api.post('/privacy/delete-request', { reason }),
  myDeletionRequest: () => api.get('/privacy/delete-request'),
  adminDeletionRequests: (params) => api.get('/privacy/admin/delete-requests', { params }),
  processDeletion: (id) => api.post(`/privacy/admin/delete-requests/${id}/process`),
}

// Polls
export const pollsAPI = {
  list: () => api.get('/polls'),
  vote: (id, option_index) => api.post(`/polls/${id}/vote`, { option_index }),
  create: (data) => api.post('/polls/admin', data),
  remove: (id) => api.delete(`/polls/admin/${id}`),
}

// Reviews
export const reviewsAPI = {
  add: (data) => api.post('/reviews', data),
  list: (type, ref, params) => api.get(`/reviews/${type}/${ref}`, { params }),
  mine: () => api.get('/reviews/mine/all'),
  remove: (id) => api.delete(`/reviews/${id}`),
}

// Bookmarks
export const bookmarksAPI = {
  add: (data) => api.post('/bookmarks', data),
  list: (target_type) => api.get('/bookmarks', { params: { target_type } }),
  remove: (id) => api.delete(`/bookmarks/${id}`),
}

// Glossary
export const glossaryAPI = {
  list: (params) => api.get('/glossary', { params }),
  search: (q) => api.get('/glossary/search', { params: { q } }),
  get: (id) => api.get(`/glossary/${id}`),
  create: (data) => api.post('/glossary/admin', data),
  remove: (id) => api.delete(`/glossary/admin/${id}`),
}

// Templates (admin)
export const templatesAPI = {
  list: (channel) => api.get('/templates', { params: { channel } }),
  create: (data) => api.post('/templates', data),
  get: (id) => api.get(`/templates/${id}`),
  update: (id, data) => api.patch(`/templates/${id}`, data),
  render: (id, variables) => api.post(`/templates/${id}/render`, { variables }),
  remove: (id) => api.delete(`/templates/${id}`),
}

// Integrations (admin)
export const integrationsAPI = {
  createApiKey: (name) => api.post('/integrations/api-keys', { name }),
  listApiKeys: () => api.get('/integrations/api-keys'),
  revokeApiKey: (id) => api.delete(`/integrations/api-keys/${id}`),
  events: () => api.get('/integrations/events'),
  createWebhook: (data) => api.post('/integrations/webhooks', data),
  listWebhooks: () => api.get('/integrations/webhooks'),
  deleteWebhook: (id) => api.delete(`/integrations/webhooks/${id}`),
}

// Surveys
export const surveysAPI = {
  list: () => api.get('/surveys'),
  get: (id) => api.get(`/surveys/${id}`),
  respond: (id, answers) => api.post(`/surveys/${id}/respond`, { answers }),
  create: (data) => api.post('/surveys/admin', data),
  results: (id) => api.get(`/surveys/admin/${id}/results`),
  remove: (id) => api.delete(`/surveys/admin/${id}`),
}

// Dashboard aggregates
export const dashboardAPI = {
  home: () => api.get('/dashboard/home'),
  quickStats: () => api.get('/dashboard/quick-stats'),
  leaderboardPreview: () => api.get('/dashboard/leaderboard-preview'),
  whatsNew: () => api.get('/dashboard/whats-new'),
}

export default api
