import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { BarChart, Bar, LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Users, Activity, TrendingUp, Star, Download, Search, Trash2, LogOut, Shield, ChevronRight, AlertCircle } from 'lucide-react'
import { useState } from 'react'
import { adminAPI, authAPI } from '../services/api'
import { useAuthStore } from '../store/authStore'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

export default function AdminPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const { logout } = useAuthStore()
  const navigate = useNavigate()
  
  const { data: stats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => adminAPI.getStats()
  })
  
  const { data: users, refetch: refetchUsers } = useQuery({
    queryKey: ['admin-users', currentPage, searchTerm],
    queryFn: () => adminAPI.getUsers({ page: currentPage, limit: 10, search: searchTerm })
  })
  
  const handleExportCSV = async () => {
    try {
      const response = await adminAPI.exportCSV()
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `users_export_${new Date().toISOString().split('T')[0]}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      toast.success('CSV exported successfully')
    } catch (error) { toast.error('Export failed') }
  }
  
  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user? This action cannot be undone.')) return
    try {
      await adminAPI.deleteUser(userId)
      toast.success('User deleted successfully')
      refetchUsers()
    } catch (error) { toast.error('Delete failed') }
  }
  
  const handleLogout = async () => {
    await authAPI.logout()
    logout()
    navigate('/')
  }
  
  const sessionsByDate = stats?.data?.sessions_by_date
    ? Object.entries(stats.data.sessions_by_date).map(([date, count]) => ({
        date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        sessions: count
      })) : []
  
  const accuracyByLesson = stats?.data?.accuracy_by_lesson
    ? Object.entries(stats.data.accuracy_by_lesson).map(([lesson, accuracy]) => ({
        lesson: `Lesson ${lesson}`,
        accuracy: Math.round(accuracy)
      })) : []
  
  const adminStats = [
    { icon: Users, title: 'Total Users', value: stats?.data?.total_users || 0, gradient: 'from-blue-500 to-indigo-600', change: '+12%' },
    { icon: Activity, title: 'Sessions Today', value: stats?.data?.sessions_today || 0, gradient: 'from-emerald-500 to-teal-600', change: '+5%' },
    { icon: TrendingUp, title: 'Avg Accuracy', value: `${Math.round(stats?.data?.avg_accuracy || 0)}%`, gradient: 'from-orange-500 to-amber-600', change: '+3%' },
    { icon: Star, title: 'Total Stars', value: stats?.data?.total_stars || 0, gradient: 'from-gold-400 to-amber-500', change: '+28' },
  ]
  
  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-neutral-900 via-neutral-900 to-neutral-800 border-b border-neutral-800 px-8 py-5 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-gradient-to-br from-red-600 to-orange-600 rounded-xl flex items-center justify-center shadow-lg">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Admin Dashboard</h1>
              <p className="text-xs text-neutral-500">SpeakEasy ASD Management Console</p>
            </div>
          </div>
          <button onClick={handleLogout}
            className="flex items-center gap-2 px-5 py-2.5 bg-neutral-800 hover:bg-neutral-700 rounded-xl transition text-sm border border-neutral-700">
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </div>
      
      <div className="max-w-7xl mx-auto p-8">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-5 mb-8">
          {adminStats.map((stat, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              whileHover={{ y: -4 }}
              className="bg-neutral-900 rounded-2xl p-6 border border-neutral-800 hover:border-neutral-700 transition-all duration-300"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 bg-gradient-to-br ${stat.gradient} rounded-xl flex items-center justify-center shadow-lg`}>
                  <stat.icon className="w-6 h-6 text-white" />
                </div>
                <span className="text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-2.5 py-1 rounded-full">{stat.change}</span>
              </div>
              <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
              <div className="text-sm text-neutral-500">{stat.title}</div>
            </motion.div>
          ))}
        </div>
        
        {/* Charts */}
        <div className="grid grid-cols-2 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-neutral-900 rounded-3xl p-6 border border-neutral-800"
          >
            <h2 className="text-lg font-bold mb-4 text-neutral-200">Sessions (Last 30 Days)</h2>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={sessionsByDate.slice(-30)}>
                <defs>
                  <linearGradient id="adminGrad1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                <XAxis dataKey="date" stroke="#525252" fontSize={11} />
                <YAxis stroke="#525252" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: '#171717', border: '1px solid #262626', borderRadius: '12px', color: '#fff' }} />
                <Area type="monotone" dataKey="sessions" stroke="#4F46E5" strokeWidth={2} fill="url(#adminGrad1)" />
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-neutral-900 rounded-3xl p-6 border border-neutral-800"
          >
            <h2 className="text-lg font-bold mb-4 text-neutral-200">Accuracy by Lesson</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={accuracyByLesson}>
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                <XAxis dataKey="lesson" stroke="#525252" fontSize={11} />
                <YAxis stroke="#525252" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: '#171717', border: '1px solid #262626', borderRadius: '12px', color: '#fff' }} />
                <Bar dataKey="accuracy" fill="#4F46E5" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </motion.div>
        </div>
        
        {/* User Management */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-neutral-900 rounded-3xl p-6 border border-neutral-800"
        >
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold">User Management</h2>
            <button onClick={handleExportCSV}
              className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-600 to-secondary-600 text-white rounded-xl hover:opacity-90 transition shadow-lg text-sm font-medium">
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
          
          {/* Search */}
          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-600" />
              <input type="text" placeholder="Search by name or email..."
                value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3.5 bg-neutral-800 border border-neutral-700 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none text-white placeholder-neutral-500 text-sm"
              />
            </div>
          </div>
          
          {/* Table */}
          <div className="overflow-x-auto rounded-xl border border-neutral-800">
            <table className="w-full">
              <thead>
                <tr className="bg-neutral-800/50">
                  <th className="text-left py-3.5 px-5 font-semibold text-neutral-400 text-xs uppercase tracking-wider">Name</th>
                  <th className="text-left py-3.5 px-5 font-semibold text-neutral-400 text-xs uppercase tracking-wider">Child</th>
                  <th className="text-left py-3.5 px-5 font-semibold text-neutral-400 text-xs uppercase tracking-wider">Email</th>
                  <th className="text-left py-3.5 px-5 font-semibold text-neutral-400 text-xs uppercase tracking-wider">Sessions</th>
                  <th className="text-left py-3.5 px-5 font-semibold text-neutral-400 text-xs uppercase tracking-wider">Stars</th>
                  <th className="text-left py-3.5 px-5 font-semibold text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users?.data?.users?.map((user, i) => (
                  <motion.tr key={user._id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="border-t border-neutral-800 hover:bg-neutral-800/30 transition"
                  >
                    <td className="py-3.5 px-5 text-sm">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center text-white font-bold text-xs">
                          {user.full_name?.charAt(0) || '?'}
                        </div>
                        {user.full_name}
                      </div>
                    </td>
                    <td className="py-3.5 px-5 text-sm text-neutral-400">{user.child_name} <span className="text-neutral-600">({user.child_age}y)</span></td>
                    <td className="py-3.5 px-5 text-sm text-neutral-400">{user.email}</td>
                    <td className="py-3.5 px-5 text-sm font-medium">{user.total_sessions}</td>
                    <td className="py-3.5 px-5 text-sm font-medium text-gold-400">{user.total_stars} ⭐</td>
                    <td className="py-3.5 px-5">
                      <button onClick={() => handleDeleteUser(user._id)}
                        className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* Pagination */}
          {users?.data && (
            <div className="flex justify-center mt-6 gap-2">
              {[...Array(users.data.pages || 1)].map((_, i) => (
                <button key={i} onClick={() => setCurrentPage(i + 1)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                    currentPage === i + 1
                      ? 'bg-gradient-to-r from-primary-600 to-secondary-600 text-white shadow-lg'
                      : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'
                  }`}>
                  {i + 1}
                </button>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
