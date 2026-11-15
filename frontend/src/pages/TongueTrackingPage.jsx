import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import {
  ScanFace, Camera, Square, Eye, Smile, Target,
  AlignCenter, Sparkles, Info, CircleDot,
} from 'lucide-react'
import toast from 'react-hot-toast'
import DashboardLayout from '../components/layout/DashboardLayout'
import { Card, StatCard, SectionTitle, Badge, GradientButton } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import { useFaceDetection } from '../hooks/useFaceDetection'

export default function TongueTrackingPage() {
  const { user } = useAuthStore()
  const [active, setActive] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const timerRef = useRef(null)
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const { faceData, startDetection, stopDetection } = useFaceDetection(videoRef, canvasRef)

  useEffect(() => {
    if (active) {
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [active])

  useEffect(() => () => {
    stopDetection()
    streamRef.current?.getTracks().forEach((track) => track.stop())
  }, [stopDetection])

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
      streamRef.current = stream
      videoRef.current.srcObject = stream
      await videoRef.current.play()
      setSeconds(0)
      setActive(true)
      startDetection()
      toast('Private camera started — processing stays on this device', { icon: '📷' })
    } catch {
      toast.error('Could not access the camera. Check browser permission and try again.')
    }
  }
  const stop = () => {
    stopDetection()
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setActive(false)
    toast.success('Camera stopped. No video was saved.')
  }
  const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
  const metrics = [
    { icon: Eye, title: 'Face Detected', value: faceData.faceDetected ? 'Yes' : 'No', sub: active ? 'Live camera' : 'Camera off', color: 'primary' },
    { icon: Smile, title: 'Mouth Opening', value: `${Math.round(faceData.mouthOpenRatio * 100)}%`, sub: 'Live opening ratio', color: 'secondary' },
    { icon: AlignCenter, title: 'Mouth Width', value: faceData.mouthWidth.toFixed(3), sub: 'Normalized distance', color: 'accent' },
    { icon: Target, title: 'Mouth Height', value: faceData.mouthHeight.toFixed(3), sub: 'Normalized distance', color: 'gold' },
  ]

  return (
    <DashboardLayout
      title="Private Mouth Tracking"
      subtitle={`Live mouth-shape practice for ${user?.child_name || user?.full_name || 'your child'}`}
      icon={ScanFace}
    >
      <div className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Camera preview */}
          <Card className="lg:col-span-2 p-6">
            <SectionTitle
              title="Live Camera"
              subtitle="Local MediaPipe face-mesh tracking"
              icon={Camera}
              action={
                <Badge color={active ? 'coral' : 'neutral'}>
                  <CircleDot className={`w-3 h-3 ${active ? 'text-coral-500 animate-pulse' : ''}`} />
                  {active ? 'LIVE' : 'Offline'}
                </Badge>
              }
            />
            <div className="relative aspect-video rounded-2xl bg-neutral-900 overflow-hidden border border-neutral-800">
              <video
                ref={videoRef}
                data-testid="tongue-camera"
                autoPlay
                muted
                playsInline
                aria-label="Private live mouth-tracking camera"
                className={`absolute inset-0 h-full w-full object-cover -scale-x-100 ${active ? 'opacity-100' : 'opacity-0'}`}
              />
              <canvas
                ref={canvasRef}
                width="640"
                height="360"
                className={`absolute inset-0 h-full w-full -scale-x-100 ${active ? 'opacity-100' : 'opacity-0'}`}
                aria-hidden="true"
              />

              {/* subtle grid backdrop */}
              <div
                className={`absolute inset-0 opacity-20 ${active ? 'pointer-events-none' : ''}`}
                style={{
                  backgroundImage:
                    'linear-gradient(#334155 1px, transparent 1px), linear-gradient(90deg, #334155 1px, transparent 1px)',
                  backgroundSize: '28px 28px',
                }}
              />

              {/* Scanning line */}
              {active && (
                <motion.div
                  className="absolute left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-secondary-400 to-transparent"
                  animate={{ top: ['10%', '90%', '10%'] }}
                  transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                />
              )}

              {/* Idle placeholder */}
              {!active && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center text-neutral-400">
                  <div className="w-16 h-16 rounded-2xl bg-neutral-800 flex items-center justify-center mb-3">
                    <Camera className="w-8 h-8" />
                  </div>
                  <p className="text-sm font-medium">Camera is off</p>
                  <p className="text-xs text-neutral-500">Press Start Camera to begin tracking</p>
                </div>
              )}

              {/* Timer badge */}
              {active && (
                <div className="absolute top-3 left-3 px-2.5 py-1 rounded-lg bg-coral-500/90 text-white text-xs font-mono font-bold flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" /> REC {fmt(seconds)}
                </div>
              )}
            </div>

            {/* Controls */}
            <div className="mt-5 flex flex-wrap items-center gap-3">
              {!active ? (
                <GradientButton onClick={start}>
                  <Camera className="w-4 h-4" /> Start Camera
                </GradientButton>
              ) : (
                <button
                  onClick={stop}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-coral-500 hover:bg-coral-600 text-white font-semibold text-sm shadow-md transition"
                >
                  <Square className="w-4 h-4 fill-white" /> Stop
                </button>
              )}
            </div>
          </Card>

          {/* Instruction card */}
          <Card className="p-6 flex flex-col">
            <SectionTitle title="Exercise" icon={Info} />
            <div className="rounded-2xl bg-gradient-to-br from-primary-500 to-secondary-500 p-6 text-white mb-4">
              <Sparkles className="w-7 h-7 mb-3" />
              <h3 className="text-lg font-bold mb-1">Open your mouth and hold</h3>
              <p className="text-sm text-white/80">Keep your face centered while the camera measures mouth opening locally.</p>
            </div>
            <ul className="space-y-3 text-sm">
              {[
                'Sit facing the light',
                'Open your mouth wide',
                'Open your mouth comfortably',
                'Hold steady — breathe normally',
              ].map((step, i) => (
                <li key={i} className="flex items-center gap-3 text-neutral-600 dark:text-neutral-300">
                  <span className="w-6 h-6 rounded-lg bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300 font-bold text-xs flex items-center justify-center shrink-0">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ul>
          </Card>
        </div>

        {/* Metrics grid */}
        <div>
          <SectionTitle title="Session Metrics" subtitle="Tracked in real time" icon={Target} />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {metrics.map((s, i) => (
              <StatCard key={s.title} {...s} delay={i * 0.1} />
            ))}
          </div>
        </div>

        <Card className="p-6">
          <SectionTitle title="Private live analysis" subtitle="Nothing is recorded or uploaded" icon={ScanFace} />
          <p className="text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
            The camera stream stays in this browser tab. SpeakEasy measures mouth geometry from live face landmarks and discards the stream as soon as you press Stop or leave the page.
          </p>
        </Card>
      </div>
    </DashboardLayout>
  )
}
