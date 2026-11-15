import { useState, useMemo, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Video, Play, Bookmark, Clock, Sparkles, History, Flame,
} from 'lucide-react'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, SectionTitle, Badge } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import pronunciationAVideo from '../assets/videos/pronounciation_a.mp4'

const CATEGORIES = ['All', 'Vowels', 'Consonants', 'Words', 'Tips']

const GRADIENTS = [
  'from-primary-500 to-indigo-600',
  'from-secondary-500 to-cyan-600',
  'from-accent-500 to-emerald-600',
  'from-gold-400 to-amber-500',
  'from-coral-500 to-rose-600',
  'from-violet-500 to-purple-600',
]

const VIDEOS = [
  { id: 1, title: 'Pronouncing அ (A)',        category: 'Vowels',     duration: '3:24', progress: 100, grad: GRADIENTS[0] },
  { id: 2, title: 'The Sound of ஆ (AA)',      category: 'Vowels',     duration: '2:58', progress: 64,  grad: GRADIENTS[1] },
  { id: 3, title: 'Mastering இ (I)',          category: 'Vowels',     duration: '3:10', progress: 0,   grad: GRADIENTS[2] },
  { id: 4, title: 'Consonant க (KA) Basics',  category: 'Consonants', duration: '4:02', progress: 42,  grad: GRADIENTS[3] },
  { id: 5, title: 'Forming ம (MA)',           category: 'Consonants', duration: '3:45', progress: 80,  grad: GRADIENTS[4] },
  { id: 6, title: 'Lip Pop ப (PA)',           category: 'Consonants', duration: '2:30', progress: 12,  grad: GRADIENTS[5] },
  { id: 7, title: 'Word Building: அம்மா',     category: 'Words',      duration: '5:18', progress: 35,  grad: GRADIENTS[1] },
  { id: 8, title: 'Everyday Words: மரம்',     category: 'Words',      duration: '4:40', progress: 0,   grad: GRADIENTS[2] },
  { id: 9, title: 'Tongue Placement Tips',    category: 'Tips',       duration: '6:05', progress: 58,  grad: GRADIENTS[0] },
]

const RECENT = [VIDEOS[0], VIDEOS[3], VIDEOS[8], VIDEOS[4], VIDEOS[6]]

export default function VideosPage() {
  const { user } = useAuthStore()
  const [filter, setFilter] = useState('All')
  const [bookmarks, setBookmarks] = useState(new Set([1, 5]))
  const videoRef = useRef(null)

  const filtered = useMemo(
    () => (filter === 'All' ? VIDEOS : VIDEOS.filter((v) => v.category === filter)),
    [filter]
  )

  const toggleBookmark = (id, title) => {
    setBookmarks((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
        toast('Removed from bookmarks', { icon: '🔖' })
      } else {
        next.add(id)
        toast.success(`Bookmarked “${title}”`)
      }
      return next
    })
  }

  const playVideo = (video) => {
    if (video.id !== 1) {
      toast('This lesson is being prepared. Try the featured A lesson now.', { icon: '🎬' })
      videoRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }
    videoRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    videoRef.current?.play().catch(() => {})
  }

  return (
    <DashboardLayout
      title="Training Videos"
      subtitle="Watch, learn, and practice Tamil pronunciation"
      icon={Video}
    >
      <div className="space-y-8">
        {/* FEATURED */}
        <Card className="overflow-hidden">
          <div className="grid lg:grid-cols-5">
            <div className="lg:col-span-3 relative aspect-video bg-gradient-to-br from-primary-600 via-primary-700 to-secondary-700 flex items-center justify-center group">
              <div className="absolute inset-0 bg-grid opacity-10" />
              <div className="absolute -right-10 -top-10 w-52 h-52 bg-white/10 rounded-full blur-3xl" />
              <video
                ref={videoRef}
                data-testid="pronunciation-video"
                controls
                preload="metadata"
                className="relative z-10 h-full w-full object-contain bg-neutral-950"
                src={pronunciationAVideo}
              >
                Your browser does not support the pronunciation video.
              </video>
            </div>
            <div className="lg:col-span-2 p-7 flex flex-col justify-center">
              <Badge color="gold" className="w-fit mb-3">
                <Flame className="w-3.5 h-3.5" /> Featured Today
              </Badge>
              <h2 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">
                Daily Lesson: The Vowel <span className="tamil-letter text-primary-600 dark:text-primary-400">அ</span>
              </h2>
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4 leading-relaxed">
                A guided walkthrough of the first Tamil vowel — mouth shape, sound, and example words to practice together.
              </p>
              <div className="flex items-center gap-4 text-sm text-neutral-500 dark:text-neutral-400">
                <span className="inline-flex items-center gap-1.5"><Clock className="w-4 h-4" /> 4:12</span>
                <span className="inline-flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-gold-500" /> Beginner</span>
              </div>
            </div>
          </div>
        </Card>

        {/* FILTER CHIPS */}
        <div className="flex flex-wrap gap-2.5">
          {CATEGORIES.map((cat) => {
            const active = filter === cat
            return (
              <button
                key={cat}
                onClick={() => setFilter(cat)}
                className={`px-4 py-2 rounded-full text-sm font-semibold transition-all ${
                  active
                    ? 'bg-gradient-to-r from-primary-500 to-secondary-500 text-white shadow-md shadow-primary-500/25'
                    : 'bg-white dark:bg-neutral-900 text-neutral-600 dark:text-neutral-300 border border-neutral-100 dark:border-neutral-800 hover:border-primary-300'
                }`}
              >
                {cat}
              </button>
            )
          })}
        </div>

        {/* GRID */}
        <div>
          <SectionTitle title="Video Library" subtitle={`${filtered.length} videos`} icon={Video} />
          <motion.div layout className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            <AnimatePresence mode="popLayout">
              {filtered.map((v, i) => (
                <motion.div
                  layout
                  key={v.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ delay: i * 0.04 }}
                  whileHover={{ y: -5 }}
                  className="bg-white dark:bg-neutral-900 rounded-3xl shadow-md border border-neutral-100 dark:border-neutral-800 overflow-hidden"
                >
                  <div className={`relative aspect-video bg-gradient-to-br ${v.grad} flex items-center justify-center group`}>
                    <div className="absolute inset-0 bg-grid opacity-10" />
                    <button
                      onClick={() => playVideo(v)}
                      aria-label={v.id === 1 ? `Play ${v.title}` : `${v.title} preview unavailable`}
                      className="relative z-10 w-14 h-14 rounded-full bg-white/90 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform"
                    >
                      <Play className="w-6 h-6 text-neutral-800 fill-neutral-800 ml-0.5" />
                    </button>
                    <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-black/60 text-white text-xs font-semibold backdrop-blur">
                      {v.duration}
                    </span>
                    <button
                      onClick={() => toggleBookmark(v.id, v.title)}
                      className="absolute top-2 right-2 w-9 h-9 rounded-full bg-black/40 backdrop-blur flex items-center justify-center hover:bg-black/60 transition"
                    >
                      <Bookmark className={`w-4 h-4 transition ${bookmarks.has(v.id) ? 'text-gold-400 fill-gold-400' : 'text-white'}`} />
                    </button>
                  </div>
                  <div className="p-4">
                    <Badge color="neutral" className="mb-2">{v.category}</Badge>
                    <h3 className="font-bold text-neutral-900 dark:text-white text-sm mb-3 leading-snug">{v.title}</h3>
                    <div className="flex items-center justify-between mb-1.5 text-xs text-neutral-400">
                      <span>{v.progress > 0 ? `${v.progress}% watched` : 'Not started'}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-neutral-100 dark:bg-neutral-800 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${v.progress}%` }}
                        transition={{ duration: 0.8, ease: 'easeOut' }}
                        className="h-full rounded-full bg-gradient-to-r from-primary-500 to-secondary-500"
                      />
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        </div>

        {/* RECENTLY WATCHED */}
        <Card className="p-6">
          <SectionTitle title="Recently Watched" subtitle="Pick up where you left off" icon={History} />
          <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin">
            {RECENT.map((v) => (
              <motion.button
                key={v.id}
                whileHover={{ y: -4 }}
                onClick={() => playVideo(v)}
                className="shrink-0 w-56 text-left"
              >
                <div className={`relative aspect-video rounded-2xl bg-gradient-to-br ${v.grad} flex items-center justify-center mb-2`}>
                  <Play className="w-8 h-8 text-white/90 fill-white/90" />
                  <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-black/60 text-white text-xs font-semibold">{v.duration}</span>
                </div>
                <div className="text-sm font-semibold text-neutral-800 dark:text-neutral-100 truncate">{v.title}</div>
                <div className="text-xs text-neutral-400">{v.category}</div>
              </motion.button>
            ))}
          </div>
        </Card>
      </div>
    </DashboardLayout>
  )
}
