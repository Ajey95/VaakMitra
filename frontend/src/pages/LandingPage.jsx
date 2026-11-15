import { useState, useEffect, useRef } from 'react'
import { Element } from 'react-scroll'
import { motion, useScroll, useTransform, AnimatePresence, useInView } from 'framer-motion'
import { 
  Target, Lock, Globe, Gamepad2, BarChart3, Brain, ArrowRight, ArrowUp,
  PlayCircle, CheckCircle, Star, Sparkles, Mail, MapPin, Phone, Award, 
  Users, Lightbulb, Shield, Mic, Camera, Heart, ChevronDown, ChevronRight,
  Zap, BookOpen, GraduationCap, Volume2, Menu, X,
  Send, Clock, Trophy, Eye, MessageCircle, HelpCircle, Plus, Minus, ArrowDown
} from 'lucide-react'
import { contactAPI } from '../services/api'
import toast from 'react-hot-toast'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import { Link as ScrollLink } from 'react-scroll'

// Import local assets
import happyBearImg from '../assets/images/happy_bear.png'
import fruitHappyImg from '../assets/images/fruit_happy.png'
import cloudAnimationImg from '../assets/images/cloud_animation.png'
import chefKidImg from '../assets/images/chef_kid.png'
import strawberryImg from '../assets/images/strawberry_cartoon.png'
import huskyImg from '../assets/images/huskey_playing_with_ball.png'
import rainbowImg from '../assets/images/rainbow_wgg.png'
import cocoImg from '../assets/images/coco_cartton.png'
import MitraRobot from '../components/three/MitraRobot'

// ─────────────────────────────────────────────────
// Animated Counter Component
// ─────────────────────────────────────────────────
function AnimatedCounter({ value, suffix = '', prefix = '', duration = 2 }) {
  const [count, setCount] = useState(0)
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true })
  
  useEffect(() => {
    if (!isInView) return
    const numericValue = parseInt(value.replace(/[^0-9]/g, ''))
    if (isNaN(numericValue)) { setCount(value); return }
    
    let start = 0
    const end = numericValue
    const stepTime = Math.abs(Math.floor((duration * 1000) / end))
    const timer = setInterval(() => {
      start += Math.ceil(end / 60)
      if (start >= end) { setCount(end); clearInterval(timer) }
      else setCount(start)
    }, stepTime)
    return () => clearInterval(timer)
  }, [isInView, value, duration])
  
  return <span ref={ref}>{prefix}{typeof count === 'number' ? count.toLocaleString() : count}{suffix}</span>
}

// ─────────────────────────────────────────────────
// Floating Particle Component
// ─────────────────────────────────────────────────
function FloatingParticles() {
  const particles = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: Math.random() * 6 + 2,
    duration: Math.random() * 10 + 8,
    delay: Math.random() * 5,
    opacity: Math.random() * 0.3 + 0.1,
  }))
  
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full bg-white"
          style={{
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            opacity: p.opacity,
          }}
          animate={{
            y: [-20, -80, -20],
            x: [-10, 10, -10],
            opacity: [p.opacity, p.opacity * 2, p.opacity],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            delay: p.delay,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  )
}

// ─────────────────────────────────────────────────
// Section Wrapper with InView Animation
// ─────────────────────────────────────────────────
function Section({ children, className = '', id }) {
  return (
    <Element name={id || ''}>
      <section className={className} id={id}>
        {children}
      </section>
    </Element>
  )
}

function SectionHeader({ badge, badgeIcon: BadgeIcon, title, titleHighlight, subtitle, dark = false }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-100px' }}
      transition={{ duration: 0.7 }}
      className="text-center mb-16 md:mb-20"
    >
      {badge && (
        <div className={`section-badge mb-6 ${dark ? 'bg-white/10 text-white border-white/20' : ''}`}>
          {BadgeIcon && <BadgeIcon className="w-4 h-4" />}
          {badge}
        </div>
      )}
      <h2 className={`section-title mb-5 ${dark ? 'text-white' : 'text-neutral-900'}`}>
        {title}{' '}
        {titleHighlight && (
          <span className={dark ? 'text-secondary-300' : 'gradient-text'}>{titleHighlight}</span>
        )}
      </h2>
      {subtitle && <p className={`section-subtitle ${dark ? 'text-neutral-300' : ''}`}>{subtitle}</p>}
    </motion.div>
  )
}


// ═══════════════════════════════════════════════════════════
// MAIN LANDING PAGE COMPONENT
// ═══════════════════════════════════════════════════════════
export default function LandingPage() {
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [openFaq, setOpenFaq] = useState(null)
  const [showBackToTop, setShowBackToTop] = useState(false)
  
  // Scroll tracking
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 50)
      setShowBackToTop(window.scrollY > 600)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])
  
  // ─── DATA ────────────────────────────────────────
  
  const navLinks = [
    { name: 'Home', to: 'home' },
    { name: 'Features', to: 'features' },
    { name: 'How It Works', to: 'how-it-works' },
    { name: 'Technology', to: 'technology' },
    { name: 'Lessons', to: 'lessons' },
    { name: 'Team', to: 'about' },
    { name: 'Contact', to: 'contact' },
  ]
  
  const features = [
    { icon: Brain, title: 'Real-Time AI Analysis', description: 'Wav2Vec2 speech recognition and MediaPipe face mesh with 468 landmarks analyze pronunciation and mouth movements in real-time, providing instant, actionable feedback.', color: 'from-indigo-500 to-purple-600' },
    { icon: Target, title: 'Personalized Therapy Paths', description: 'Adaptive AI intelligently adjusts difficulty based on each child\'s unique progress, ensuring every session is challenging yet achievable for maximum growth.', color: 'from-blue-500 to-cyan-500' },
    { icon: Lock, title: 'Privacy-First Architecture', description: 'All speech and face data is processed locally with edge computing — zero cloud storage, zero data sharing. Your child\'s privacy is our highest priority.', color: 'from-emerald-500 to-teal-600' },
    { icon: Gamepad2, title: 'Gamified Star Rewards', description: 'Earn 1, 2, or 3 stars per lesson with confetti celebrations, sound effects, and progress milestones. Children stay motivated through positive reinforcement.', color: 'from-amber-500 to-orange-500' },
    { icon: Globe, title: 'Tamil & Telugu Phonetics', description: 'Native Dravidian language support with culturally relevant lessons. Practice அ, ஆ, ல, த and words like அம்மா (Amma) and அப்பா (Appa) with precision.', color: 'from-pink-500 to-rose-600' },
    { icon: BarChart3, title: 'Comprehensive Analytics', description: 'Detailed progress charts, accuracy trends, session history, and exportable reports help parents and therapists track every milestone with data-driven insights.', color: 'from-violet-500 to-fuchsia-600' },
    { icon: Camera, title: '3D Candle Blow Test', description: 'An innovative Three.js-powered 3D candle simulation tests breath control and airflow — essential for word pronunciation mastery like "Amma" and "Appa".', color: 'from-cyan-500 to-blue-600' },
    { icon: Shield, title: 'Evidence-Based Methods', description: 'Built on proven ASD speech therapy research: visual supports, immediate reinforcement, multimodal feedback, and consistent repetition drive real outcomes.', color: 'from-red-500 to-pink-600' },
  ]
  
  const steps = [
    { num: '01', icon: '👤', title: 'Create Your Account', description: 'Register in under 2 minutes with your child\'s details. We personalize the experience based on age and learning needs.', bgColor: 'from-indigo-500 to-indigo-600' },
    { num: '02', icon: '📖', title: 'Choose a Lesson', description: 'Pick from 6 progressive lessons — 4 Tamil letters and 2 meaningful words. Each lesson follows a structured 5-slide therapy flow.', bgColor: 'from-purple-500 to-purple-600' },
    { num: '03', icon: '🎤', title: 'Practice with AI', description: 'Your child sees the letter, watches mouth animations, then practices with live camera and microphone evaluation powered by real-time ML.', bgColor: 'from-cyan-500 to-cyan-600' },
    { num: '04', icon: '⭐', title: 'Earn Stars & Grow', description: 'Receive instant star rewards (up to 3★) with confetti celebrations. Track progress on your dashboard and watch accuracy improve over time.', bgColor: 'from-amber-500 to-amber-600' },
  ]
  
  const technologies = [
    { name: 'React 18', category: 'Frontend', desc: 'Modern UI with hooks & concurrent features' },
    { name: 'FastAPI', category: 'Backend', desc: 'High-performance Python async API framework' },
    { name: 'Wav2Vec2', category: 'AI/ML', desc: 'Facebook\'s pre-trained speech recognition' },
    { name: 'MediaPipe', category: 'AI/ML', desc: 'Google\'s face mesh with 468 landmarks' },
    { name: 'Three.js', category: '3D', desc: 'Interactive 3D candle simulation' },
    { name: 'MongoDB', category: 'Database', desc: 'Flexible document store with Motor async' },
    { name: 'Framer Motion', category: 'Animation', desc: 'Production-grade motion library' },
    { name: 'TailwindCSS', category: 'Styling', desc: 'Utility-first CSS for rapid UI' },
  ]
  
  const lessons = [
    { id: 1, symbol: 'அ', english: 'A', pronunciation: 'ah', type: 'Letter', difficulty: 1, color: 'from-blue-500 to-indigo-600' },
    { id: 2, symbol: 'ஆ', english: 'AA', pronunciation: 'aah', type: 'Letter', difficulty: 1, color: 'from-purple-500 to-violet-600' },
    { id: 3, symbol: 'ல', english: 'LA', pronunciation: 'la', type: 'Letter', difficulty: 2, color: 'from-emerald-500 to-teal-600' },
    { id: 4, symbol: 'த', english: 'TA', pronunciation: 'ta', type: 'Letter', difficulty: 2, color: 'from-orange-500 to-red-600' },
    { id: 5, symbol: 'அம்மா', english: 'AMMA', pronunciation: 'ah-mm-aa', type: 'Word', difficulty: 3, color: 'from-pink-500 to-rose-600' },
    { id: 6, symbol: 'அப்பா', english: 'APPA', pronunciation: 'ah-pp-aa', type: 'Word', difficulty: 3, color: 'from-cyan-500 to-blue-600' },
  ]
  
  const statistics = [
    { value: '10000', suffix: '+', label: 'Children with ASD Worldwide', icon: Users },
    { value: '88', suffix: '%', label: 'AI Recognition Accuracy', icon: Target },
    { value: '468', suffix: '', label: 'Face Mesh Landmarks', icon: Eye },
    { value: '100', suffix: '%', label: 'Privacy Protected', icon: Lock },
  ]
  
  const team = [
    { name: 'Rohith Kumar D', id: 'CB.SC.U4CSE23018', role: 'Lead Developer', gradient: 'from-indigo-500 to-purple-600' },
    { name: 'T Venkataramana', id: 'CB.SC.U4CSE23055', role: 'AI Engineer', gradient: 'from-blue-500 to-cyan-600' },
    { name: 'VAB Jashwanth Reddy', id: 'CB.SC.U4CSE23058', role: 'Frontend Developer', gradient: 'from-emerald-500 to-teal-600' },
    { name: 'C Kalyan Kumar Reddy', id: 'CB.SC.U4CSE23060', role: 'Backend Developer', gradient: 'from-orange-500 to-amber-600' },
    { name: 'Hemanth Sholingaram', id: 'CB.SC.U4CSE23446', role: 'ML Specialist', gradient: 'from-pink-500 to-rose-600' },
  ]
  
  const testimonials = [
    { text: "SpeakEasy has been a game-changer for our family. My son looks forward to his therapy sessions now — he actually asks to practice! The AI feedback is remarkably accurate.", author: "Priya R.", role: "Parent, Chennai", rating: 5 },
    { text: "As a speech therapist, I'm deeply impressed by the technical accuracy of the Wav2Vec2 integration. The real-time face mesh analysis provides insights I can't get in traditional sessions.", author: "Dr. Kavitha S.", role: "Speech Therapist, Coimbatore", rating: 5 },
    { text: "The gamification is brilliant — my daughter earned all her stars and the confetti celebrations make her so happy. The Tamil phonetics support is exactly what we needed.", author: "Suresh M.", role: "Parent, Madurai", rating: 5 },
    { text: "Finally, a tool that properly handles Dravidian phonetics. The candle blow test for words is an innovative approach to testing breath control. Outstanding work by Team 96!", author: "Dr. Anand K.", role: "Pediatric Specialist, Bangalore", rating: 5 },
  ]
  
  const faqs = [
    { q: 'What age group is SpeakEasy ASD designed for?', a: 'SpeakEasy ASD is designed specifically for children aged 4–12 with Autism Spectrum Disorder (ASD). The lessons are calibrated for different difficulty levels, starting with simple Tamil vowels and progressing to meaningful words. The gamified interface and star reward system are designed to engage young learners.' },
    { q: 'How does the AI speech evaluation work?', a: 'We use Facebook\'s Wav2Vec2 pre-trained model for speech-to-text recognition, combined with MFCC (Mel-Frequency Cepstral Coefficients) feature extraction. The system compares the child\'s pronunciation against reference templates using Levenshtein distance and MFCC similarity. The final accuracy score uses a weighted formula: 60% pronunciation match + 40% MFCC similarity.' },
    { q: 'Is my child\'s data safe and private?', a: 'Absolutely. Privacy is our #1 priority. All speech and face analysis data is processed locally using edge computing — we never store raw audio or video on servers. Authentication uses JWT tokens with HTTP-only cookies (preventing XSS attacks), passwords are hashed with bcrypt (10 rounds), and we have strict CORS policies. Zero data is shared with third parties.' },
    { q: 'What is the 3D Candle Blow Test?', a: 'The Candle Blow Test is an innovative assessment for word-level lessons (அம்மா and அப்பா). Using Three.js, we render an interactive 3D candle that responds to the child\'s breath and pronunciation. For "Amma" (a sustained nasal sound), the goal is to keep the flame lit. For "Appa" (a plosive sound), the goal is to blow it out. The system measures airflow using energy (RMS amplitude) and zero-crossing rate.' },
    { q: 'What languages are currently supported?', a: 'Currently, SpeakEasy supports Tamil phonetics with 6 progressive lessons: 4 Tamil letters (அ, ஆ, ல, த) and 2 words (அம்மா, அப்பா). Our roadmap includes Telugu, Hindi, Malayalam, and English support. The architecture is designed to be language-agnostic — adding new languages requires only new reference audio templates and pronunciation mappings.' },
    { q: 'Can therapists and parents both use the platform?', a: 'Yes! Parents register and manage their child\'s account, view progress dashboards, track accuracy charts, and monitor star achievements. We also provide an Admin Dashboard with full analytics — user management, session charts, accuracy-by-lesson breakdowns, and CSV exports for clinical documentation.' },
  ]
  
  const handleContactSubmit = async (e) => {
    e.preventDefault()
    const formData = new FormData(e.target)
    const data = {
      name: formData.get('name'),
      email: formData.get('email'),
      message: formData.get('message')
    }
    try {
      await contactAPI.submitContact(data)
      toast.success('Thank you! We\'ll get back to you soon.')
      e.target.reset()
    } catch (error) {
      toast.error('Failed to send message. Please try again.')
    }
  }
  
  const scrollToTop = () => window.scrollTo({ top: 0, behavior: 'smooth' })

  // ─── RENDER ─────────────────────────────────────
  
  return (
    <div className="min-h-screen bg-white overflow-x-hidden">
      
      {/* ═══════════════════════════════════════════
          1. PREMIUM GLASSMORPHIC NAVBAR
      ═══════════════════════════════════════════ */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        scrolled 
          ? 'bg-white/80 backdrop-blur-xl shadow-lg shadow-neutral-900/5 border-b border-neutral-200/50' 
          : 'bg-transparent'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            {/* Logo */}
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3 cursor-pointer"
              onClick={scrollToTop}
            >
              <div className="relative">
                <div className="w-12 h-12 bg-gradient-to-br from-primary-600 to-secondary-500 rounded-2xl flex items-center justify-center shadow-lg shadow-primary-500/25 rotate-3 hover:rotate-0 transition-transform duration-300">
                  <span className="text-white font-bold text-xl">SE</span>
                </div>
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-accent-500 rounded-full border-2 border-white animate-pulse" />
              </div>
              <div>
                <div className={`font-bold text-xl tracking-tight ${scrolled ? 'text-neutral-900' : 'text-white'}`}>SpeakEasy</div>
                <div className={`text-[11px] font-medium tracking-widest uppercase ${scrolled ? 'text-primary-600' : 'text-primary-200'}`}>ASD Therapy</div>
              </div>
            </motion.div>
            
            {/* Desktop Nav Links */}
            <div className="hidden lg:flex items-center gap-1">
              {navLinks.map((link) => (
                <ScrollLink
                  key={link.to}
                  to={link.to}
                  smooth={true}
                  duration={600}
                  offset={-80}
                  spy={true}
                  activeClass="!text-primary-600 !bg-primary-50"
                  className={`px-4 py-2 rounded-xl text-sm font-medium cursor-pointer transition-all duration-300 ${
                    scrolled ? 'text-neutral-600 hover:text-primary-600 hover:bg-primary-50' : 'text-white/80 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {link.name}
                </ScrollLink>
              ))}
            </div>
            
            {/* CTA Buttons */}
            <div className="hidden lg:flex items-center gap-3">
              <button
                onClick={() => navigate('/login')}
                className={`px-5 py-2.5 rounded-xl font-medium text-sm transition-all duration-300 ${
                  scrolled ? 'text-neutral-700 hover:text-primary-600 hover:bg-primary-50' : 'text-white/90 hover:text-white hover:bg-white/10'
                }`}
              >
                Sign In
              </button>
              <button
                onClick={() => navigate('/register')}
                className="btn-primary !px-6 !py-2.5 !text-sm !rounded-xl"
              >
                Get Started Free
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            </div>
            
            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className={`lg:hidden p-2 rounded-xl transition ${scrolled ? 'text-neutral-700' : 'text-white'}`}
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
        
        {/* Mobile Menu */}
        <AnimatePresence>
          {mobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="lg:hidden bg-white border-t border-neutral-100 shadow-xl"
            >
              <div className="px-4 py-6 space-y-2">
                {navLinks.map((link) => (
                  <ScrollLink
                    key={link.to}
                    to={link.to}
                    smooth={true}
                    duration={600}
                    offset={-80}
                    className="block px-4 py-3 text-neutral-700 hover:text-primary-600 hover:bg-primary-50 rounded-xl font-medium cursor-pointer transition"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    {link.name}
                  </ScrollLink>
                ))}
                <div className="pt-4 space-y-3 border-t border-neutral-100 mt-4">
                  <button onClick={() => { navigate('/login'); setMobileMenuOpen(false) }} className="w-full py-3 text-neutral-700 font-semibold rounded-xl border-2 border-neutral-200 hover:border-primary-500 transition">
                    Sign In
                  </button>
                  <button onClick={() => { navigate('/register'); setMobileMenuOpen(false) }} className="w-full py-3 btn-primary !rounded-xl">
                    Get Started Free
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* ═══════════════════════════════════════════
          2. CINEMATIC HERO SECTION
      ═══════════════════════════════════════════ */}
      <Section id="home">
        <div className="relative min-h-screen flex items-center bg-hero overflow-hidden">
          <FloatingParticles />
          
          {/* Gradient orbs */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden">
            <motion.div animate={{ scale: [1, 1.3, 1], rotate: [0, 180, 360] }} transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
              className="absolute -top-40 -left-40 w-[600px] h-[600px] bg-primary-500/10 rounded-full blur-3xl" />
            <motion.div animate={{ scale: [1.2, 1, 1.2], rotate: [180, 0, 180] }} transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
              className="absolute -bottom-40 -right-40 w-[500px] h-[500px] bg-secondary-500/10 rounded-full blur-3xl" />
            <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
              className="absolute top-1/3 left-1/2 w-[400px] h-[400px] bg-accent-500/5 rounded-full blur-3xl" />
          </div>
          
          {/* Grid overlay */}
          <div className="absolute inset-0 bg-grid opacity-10 pointer-events-none" />
          
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 pt-28 pb-20">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              {/* Left: Content */}
              <motion.div
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.9, delay: 0.2 }}
              >
                {/* Badge */}
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.5 }}
                  className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-md text-white/90 px-5 py-2.5 rounded-full mb-8 border border-white/20"
                >
                  <span className="w-2 h-2 bg-accent-400 rounded-full animate-pulse" />
                  <span className="text-sm font-medium">Powered by Wav2Vec2 & MediaPipe AI</span>
                </motion.div>
                
                {/* Title */}
                <h1 className="hero-title font-bold text-white mb-6 text-balance">
                  Every Child{' '}
                  <span className="relative inline-block">
                    <span className="relative z-10 text-transparent bg-clip-text bg-gradient-to-r from-secondary-300 via-accent-300 to-secondary-300">
                      Deserves
                    </span>
                    <motion.span
                      animate={{ width: ['0%', '100%'] }}
                      transition={{ delay: 1.2, duration: 0.8, ease: 'easeOut' }}
                      className="absolute bottom-2 left-0 h-3 bg-secondary-500/20 rounded-full z-0"
                    />
                  </span>{' '}
                  A Voice
                </h1>
                
                {/* Subtitle */}
                <p className="text-lg md:text-xl text-neutral-300 mb-10 leading-relaxed max-w-xl">
                  The world's most advanced, privacy-first speech therapy platform for children with Autism Spectrum Disorder. Combining real-time AI evaluation, gamified Tamil phonetics, and evidence-based methods in one beautiful experience.
                </p>
                
                {/* CTAs */}
                <div className="flex flex-col sm:flex-row gap-4 mb-14">
                  <motion.button
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => navigate('/register')}
                    className="group px-8 py-4 bg-white text-primary-700 rounded-2xl font-bold text-lg shadow-xl shadow-white/10 flex items-center justify-center gap-2 hover:shadow-2xl transition-all duration-300"
                  >
                    Start Free Today
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </motion.button>
                  
                  <ScrollLink
                    to="how-it-works"
                    smooth={true}
                    duration={600}
                    offset={-80}
                  >
                    <motion.button
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.98 }}
                      className="w-full sm:w-auto px-8 py-4 border-2 border-white/25 hover:border-white/50 text-white rounded-2xl font-bold text-lg flex items-center justify-center gap-2 hover:bg-white/5 transition-all duration-300 cursor-pointer"
                    >
                      <PlayCircle className="w-5 h-5" />
                      See How It Works
                    </motion.button>
                  </ScrollLink>
                </div>
                
                {/* Statistics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                  {statistics.map((stat, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.8 + i * 0.15 }}
                      className="text-center"
                    >
                      <div className="text-3xl md:text-4xl font-bold text-white mb-1">
                        <AnimatedCounter value={stat.value} suffix={stat.suffix} />
                      </div>
                      <div className="text-xs text-neutral-400 font-medium">{stat.label}</div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
              
              {/* Right: MITRA 3D Robot Companion */}
              <motion.div
                initial={{ opacity: 0, x: 60 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.9, delay: 0.5 }}
                className="relative hidden lg:flex flex-col items-center justify-center"
              >
                {/* Robot */}
                <MitraRobot
                  mood="happy"
                  size={480}
                  showBubble
                  message="Hi! I'm MITRA — your speech companion! 👋"
                  autoRotate={false}
                  zoom={1.1}
                  className="w-full"
                />

                {/* Floating badge — top right */}
                <motion.div
                  animate={{ y: [0, -12, 0] }}
                  transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                  className="absolute top-8 -right-4 glass rounded-2xl p-4 shadow-premium"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-accent-400 to-emerald-500 rounded-xl flex items-center justify-center shadow-lg">
                      <CheckCircle className="w-7 h-7 text-white" />
                    </div>
                    <div>
                      <div className="font-bold text-neutral-900 text-lg">88% Accuracy</div>
                      <div className="text-xs text-neutral-500">AI Recognition Rate</div>
                    </div>
                  </div>
                </motion.div>

                {/* Floating badge — bottom left */}
                <motion.div
                  animate={{ y: [0, 10, 0] }}
                  transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
                  className="absolute bottom-8 -left-4 glass rounded-2xl p-4 shadow-premium"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-gold-400 to-amber-500 rounded-xl flex items-center justify-center shadow-lg">
                      <Star className="w-7 h-7 text-white" />
                    </div>
                    <div>
                      <div className="font-bold text-neutral-900 text-lg">3-Star</div>
                      <div className="text-xs text-neutral-500">Reward System</div>
                    </div>
                  </div>
                </motion.div>

                {/* Floating Tamil letter badge */}
                <motion.div
                  animate={{ y: [0, -8, 0], rotate: [-3, 3, -3] }}
                  transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
                  className="absolute top-1/2 -left-6 glass rounded-2xl p-3 shadow-premium"
                >
                  <div className="text-center">
                    <div className="tamil-letter text-3xl font-bold text-primary-600">அ</div>
                    <div className="text-[10px] text-neutral-500 font-medium">Tamil</div>
                  </div>
                </motion.div>
              </motion.div>
            </div>
          </div>
          
          {/* Scroll indicator */}
          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="absolute bottom-8 left-1/2 -translate-x-1/2 text-white/40"
          >
            <ArrowDown className="w-6 h-6" />
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          3. ANIMATED MARQUEE BANNER
      ═══════════════════════════════════════════ */}
      <div className="relative bg-gradient-to-r from-primary-600 via-primary-500 to-secondary-600 py-5 overflow-hidden">
        <div className="absolute inset-0 bg-dots opacity-10" />
        {/* Row 1 */}
        <div className="marquee-container mb-2">
          <div className="marquee-track">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="flex items-center gap-12 pr-12 text-white/90 font-semibold text-sm">
                <span className="flex items-center gap-2"><Brain className="w-4 h-4 text-secondary-200" /> Real-Time Wav2Vec2 Speech Recognition</span>
                <span className="flex items-center gap-2"><Lock className="w-4 h-4 text-accent-300" /> 100% Privacy-First Edge Computing</span>
                <span className="flex items-center gap-2"><Camera className="w-4 h-4 text-pink-200" /> 468 MediaPipe Face Landmarks</span>
                <span className="flex items-center gap-2"><BarChart3 className="w-4 h-4 text-amber-200" /> Comprehensive Progress Analytics</span>
                <span className="flex items-center gap-2"><Gamepad2 className="w-4 h-4 text-green-200" /> Gamified Star Reward System</span>
                <span className="flex items-center gap-2"><Globe className="w-4 h-4 text-cyan-200" /> Tamil & Telugu Phonetics Support</span>
                <span className="flex items-center gap-2"><Trophy className="w-4 h-4 text-yellow-200" /> Evidence-Based ASD Therapy</span>
                <span className="flex items-center gap-2"><Heart className="w-4 h-4 text-red-200" /> Built with Love for Children</span>
              </div>
            ))}
          </div>
        </div>
        {/* Row 2 — reverse */}
        <div className="marquee-container">
          <div className="marquee-track-reverse">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="flex items-center gap-12 pr-12 text-white/60 font-medium text-xs">
                <span>🎯 Personalized Learning Paths</span>
                <span>🔒 Zero Cloud Storage</span>
                <span>🤖 AI-Powered Feedback</span>
                <span>📊 Data-Driven Insights</span>
                <span>🎮 Interactive 3D Candle Test</span>
                <span>⭐ Up to 3 Stars Per Lesson</span>
                <span>🗣️ Pronunciation Accuracy Scoring</span>
                <span>👨‍🏫 Therapist-Grade Evaluation</span>
                <span>🌍 SDG 3 • SDG 4 • SDG 10 Aligned</span>
                <span>🏆 Amrita Vishwa Vidyapeetham — Team 96</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════
          4. FEATURES SECTION
      ═══════════════════════════════════════════ */}
      <Section id="features" className="py-28 bg-white relative">
        <div className="absolute inset-0 bg-gradient-mesh opacity-50" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <SectionHeader
            badge="Why Choose Us"
            badgeIcon={Award}
            title="Cutting-Edge Features for"
            titleHighlight="Real Results"
            subtitle="Every feature is purpose-built to make speech therapy engaging, effective, and accessible for children with Autism Spectrum Disorder."
          />
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-80px' }}
                transition={{ delay: i * 0.08, duration: 0.6 }}
                whileHover={{ y: -8 }}
                className="group bg-white rounded-3xl p-7 border-2 border-neutral-100 hover:border-primary-200 hover:shadow-xl transition-all duration-400 relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-primary-50 to-transparent rounded-bl-full opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className={`relative z-10 w-14 h-14 bg-gradient-to-br ${feature.color} rounded-2xl flex items-center justify-center mb-5 shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                  <feature.icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="relative z-10 text-lg font-bold text-neutral-900 mb-3">{feature.title}</h3>
                <p className="relative z-10 text-sm text-neutral-500 leading-relaxed">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          5. HOW IT WORKS — TIMELINE
      ═══════════════════════════════════════════ */}
      <Section id="how-it-works" className="py-28 bg-neutral-50 relative overflow-hidden">
        <div className="absolute inset-0 bg-dots opacity-30" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <SectionHeader
            badge="Simple Process"
            badgeIcon={Lightbulb}
            title="Start Therapy in"
            titleHighlight="4 Easy Steps"
            subtitle="From registration to your child's first star — it takes less than 5 minutes to begin. Our guided process makes speech therapy accessible to every family."
          />
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 relative">
            {/* Connecting line */}
            <div className="hidden lg:block absolute top-28 left-[12%] right-[12%] h-0.5 bg-gradient-to-r from-indigo-300 via-purple-300 via-cyan-300 to-amber-300" />
            
            {steps.map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15, duration: 0.6 }}
                className="text-center relative"
              >
                {/* Number circle */}
                <div className="relative mx-auto mb-8">
                  <motion.div
                    whileHover={{ scale: 1.1, rotate: 10 }}
                    className={`w-24 h-24 bg-gradient-to-br ${step.bgColor} rounded-3xl flex items-center justify-center text-5xl mx-auto shadow-xl border-4 border-white relative z-10 rotate-3`}
                  >
                    {step.icon}
                  </motion.div>
                  <div className="absolute -top-2 -right-2 bg-white text-primary-600 font-bold text-xs w-8 h-8 rounded-full flex items-center justify-center shadow-md border-2 border-primary-100 z-20">
                    {step.num}
                  </div>
                </div>
                
                <div className="bg-white rounded-2xl p-6 shadow-md border border-neutral-100 hover:shadow-lg transition-shadow">
                  <h3 className="text-lg font-bold text-neutral-900 mb-2">{step.title}</h3>
                  <p className="text-sm text-neutral-500 leading-relaxed">{step.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
          
          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mt-16"
          >
            <button onClick={() => navigate('/register')} className="btn-primary text-lg">
              Begin Your Journey
              <ArrowRight className="w-5 h-5 ml-2" />
            </button>
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          6. TECHNOLOGY SHOWCASE
      ═══════════════════════════════════════════ */}
      <Section id="technology" className="py-28 bg-neutral-950 text-white relative overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-5" />
        <FloatingParticles />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <SectionHeader
            badge="Tech Stack"
            badgeIcon={Zap}
            title="Built With"
            titleHighlight="World-Class Technology"
            subtitle="A carefully curated stack combining the best in AI/ML, modern web development, and 3D graphics to deliver a seamless therapy experience."
            dark
          />
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            {technologies.map((tech, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                whileHover={{ y: -6, scale: 1.02 }}
                className="glass-dark rounded-2xl p-6 hover:bg-white/10 transition-all duration-300 group"
              >
                <div className="text-xs text-primary-300 font-semibold uppercase tracking-wider mb-3">{tech.category}</div>
                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-secondary-300 transition-colors">{tech.name}</h3>
                <p className="text-sm text-neutral-400 leading-relaxed">{tech.desc}</p>
              </motion.div>
            ))}
          </div>
          
          {/* Architecture summary */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mt-16 glass-dark rounded-3xl p-8 md:p-12"
          >
            <div className="grid md:grid-cols-3 gap-8 text-center">
              <div>
                <div className="text-4xl font-bold text-secondary-300 mb-2">5-Slide</div>
                <div className="text-neutral-400 text-sm">Structured Therapy Flow per Lesson</div>
                <div className="text-neutral-500 text-xs mt-2">Picture → Animation → Evaluation → Candle Test → Rewards</div>
              </div>
              <div>
                <div className="text-4xl font-bold text-accent-300 mb-2">3-Layer</div>
                <div className="text-neutral-400 text-sm">ML Services Architecture</div>
                <div className="text-neutral-500 text-xs mt-2">Speech Evaluator • Face Analyzer • Reward Engine</div>
              </div>
              <div>
                <div className="text-4xl font-bold text-gold-300 mb-2">6 APIs</div>
                <div className="text-neutral-400 text-sm">RESTful + WebSocket Endpoints</div>
                <div className="text-neutral-500 text-xs mt-2">Auth • Therapy • Evaluation • Progress • Admin • Contact</div>
              </div>
            </div>
          </motion.div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          7. TAMIL ALPHABET PREVIEW
      ═══════════════════════════════════════════ */}
      <Section id="lessons" className="py-28 bg-white relative">
        <div className="absolute inset-0 bg-gradient-mesh opacity-30" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <SectionHeader
            badge="6 Progressive Lessons"
            badgeIcon={BookOpen}
            title="Master Tamil"
            titleHighlight="Letters & Words"
            subtitle="From simple vowels to meaningful words — each lesson follows a structured therapy flow designed by speech therapy experts and validated with real AI evaluation."
          />
          
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {lessons.map((lesson, i) => (
              <motion.div
                key={lesson.id}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                whileHover={{ y: -6, scale: 1.02 }}
                className="group bg-white rounded-3xl p-8 border-2 border-neutral-100 hover:border-primary-200 shadow-md hover:shadow-xl transition-all duration-300 relative overflow-hidden cursor-pointer"
                onClick={() => navigate('/register')}
              >
                {/* Background gradient on hover */}
                <div className={`absolute inset-0 bg-gradient-to-br ${lesson.color} opacity-0 group-hover:opacity-5 transition-opacity duration-500`} />
                
                <div className="relative z-10">
                  <div className="flex justify-between items-start mb-6">
                    <div className={`tamil-letter text-5xl md:text-6xl font-bold bg-gradient-to-br ${lesson.color} bg-clip-text text-transparent`}>
                      {lesson.symbol}
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span className={`text-xs font-bold px-3 py-1 rounded-full bg-gradient-to-r ${lesson.color} text-white`}>
                        {lesson.type}
                      </span>
                      <div className="flex gap-0.5">
                        {[...Array(3)].map((_, j) => (
                          <Star key={j} className={`w-4 h-4 ${j < lesson.difficulty ? 'text-gold-400 fill-gold-400' : 'text-neutral-200'}`} />
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-2xl font-bold text-neutral-900 mb-1">{lesson.english}</div>
                  <div className="text-sm text-neutral-500 mb-4">Pronounced: <span className="font-semibold text-primary-600">"{lesson.pronunciation}"</span></div>
                  
                  <div className="flex items-center gap-2 text-xs text-neutral-400">
                    <Volume2 className="w-3.5 h-3.5" />
                    <span>5-slide therapy • AI evaluation • Star rewards</span>
                  </div>
                </div>
                
                {/* Arrow */}
                <div className="absolute bottom-6 right-6 opacity-0 group-hover:opacity-100 transition-opacity">
                  <ArrowRight className="w-5 h-5 text-primary-500" />
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          8. TESTIMONIALS
      ═══════════════════════════════════════════ */}
      <Section className="py-28 bg-neutral-50 relative">
        <div className="absolute inset-0 bg-dots opacity-20" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <SectionHeader
            badge="Testimonials"
            badgeIcon={MessageCircle}
            title="Trusted by Parents &"
            titleHighlight="Therapists"
            subtitle="Real stories from families and professionals who have experienced the transformative power of AI-assisted speech therapy."
          />
          
          <div className="grid md:grid-cols-2 gap-6">
            {testimonials.map((t, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="bg-white rounded-3xl p-8 shadow-md border border-neutral-100 hover:shadow-lg transition-shadow duration-300 relative"
              >
                {/* Quote mark */}
                <div className="absolute top-6 right-8 text-6xl text-primary-100 font-serif leading-none">"</div>
                
                <div className="flex gap-1 mb-5">
                  {[...Array(t.rating)].map((_, j) => (
                    <Star key={j} className="w-5 h-5 text-gold-400 fill-gold-400" />
                  ))}
                </div>
                <p className="text-neutral-600 mb-6 leading-relaxed text-[15px] relative z-10">"{t.text}"</p>
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
                    {t.author.charAt(0)}
                  </div>
                  <div>
                    <div className="font-semibold text-neutral-900">{t.author}</div>
                    <div className="text-xs text-neutral-500">{t.role}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          9. FAQ ACCORDION
      ═══════════════════════════════════════════ */}
      <Section className="py-28 bg-white relative">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <SectionHeader
            badge="FAQ"
            badgeIcon={HelpCircle}
            title="Frequently Asked"
            titleHighlight="Questions"
            subtitle="Everything you need to know about SpeakEasy ASD. Can't find what you're looking for? Contact our team below."
          />
          
          <div className="space-y-4">
            {faqs.map((faq, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className="border-2 border-neutral-100 rounded-2xl overflow-hidden hover:border-primary-200 transition-colors"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between p-6 text-left"
                >
                  <span className="font-semibold text-neutral-900 pr-4">{faq.q}</span>
                  <motion.div
                    animate={{ rotate: openFaq === i ? 180 : 0 }}
                    transition={{ duration: 0.3 }}
                    className="flex-shrink-0"
                  >
                    <ChevronDown className={`w-5 h-5 transition-colors ${openFaq === i ? 'text-primary-600' : 'text-neutral-400'}`} />
                  </motion.div>
                </button>
                <AnimatePresence>
                  {openFaq === i && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <div className="px-6 pb-6 text-neutral-600 leading-relaxed text-[15px] border-t border-neutral-100 pt-4">
                        {faq.a}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          10. TEAM SECTION
      ═══════════════════════════════════════════ */}
      <Section id="about" className="py-28 bg-neutral-50 relative">
        <div className="absolute inset-0 bg-gradient-mesh opacity-30" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <SectionHeader
            badge="Our Team"
            badgeIcon={Users}
            title="Meet"
            titleHighlight="Team 96"
            subtitle="A passionate team of engineers, designers, and researchers from Amrita Vishwa Vidyapeetham, united by a mission to make speech therapy accessible to every child."
          />
          
          {/* Team grid */}
          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-5 mb-12">
            {team.map((member, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                whileHover={{ y: -6 }}
                className="bg-white rounded-2xl p-6 shadow-md border border-neutral-100 text-center hover:shadow-xl transition-all duration-300"
              >
                <div className={`w-20 h-20 bg-gradient-to-br ${member.gradient} rounded-2xl flex items-center justify-center text-white text-3xl font-bold mx-auto mb-4 shadow-lg rotate-3 group-hover:rotate-0 transition-transform`}>
                  {member.name.charAt(0)}
                </div>
                <h3 className="font-bold text-neutral-900 mb-1 text-sm">{member.name}</h3>
                <p className="text-xs text-primary-600 font-semibold mb-2">{member.role}</p>
                <p className="text-[10px] text-neutral-400 font-mono">{member.id}</p>
              </motion.div>
            ))}
          </div>
          
          {/* Project Guide */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="bg-gradient-to-r from-primary-600 via-primary-700 to-secondary-700 rounded-3xl p-10 text-center text-white shadow-2xl relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-grid opacity-5" />
            <div className="relative z-10">
              <div className="w-24 h-24 bg-white/15 backdrop-blur-sm rounded-3xl flex items-center justify-center text-5xl mx-auto mb-5 border-2 border-white/20 shadow-xl">
                👨‍🏫
              </div>
              <h3 className="text-3xl font-bold mb-2">Dr. Venkataraman D</h3>
              <p className="text-primary-200 text-lg mb-1">Assistant Professor | Department of CSE</p>
              <p className="text-white/80 font-medium">Project Guide — Amrita Vishwa Vidyapeetham, Coimbatore</p>
            </div>
          </motion.div>
          
          {/* SDGs */}
          <div className="text-center mt-12">
            <p className="text-neutral-600 font-semibold mb-6 text-lg">Aligned with UN Sustainable Development Goals</p>
            <div className="flex justify-center gap-4 flex-wrap">
              {[
                { num: 3, name: 'Good Health', color: 'from-green-500 to-emerald-600' },
                { num: 4, name: 'Quality Education', color: 'from-red-500 to-rose-600' },
                { num: 9, name: 'Innovation', color: 'from-orange-500 to-amber-600' },
                { num: 10, name: 'Reduced Inequality', color: 'from-pink-500 to-fuchsia-600' }
              ].map((sdg) => (
                <motion.div
                  key={sdg.num}
                  whileHover={{ scale: 1.08, rotate: 3 }}
                  className={`bg-gradient-to-br ${sdg.color} text-white rounded-2xl p-4 shadow-lg w-28 h-28 flex flex-col items-center justify-center`}
                >
                  <div className="text-sm font-bold opacity-70">SDG</div>
                  <div className="text-3xl font-bold">{sdg.num}</div>
                  <div className="text-[10px] mt-1 opacity-80">{sdg.name}</div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          11. CONTACT SECTION
      ═══════════════════════════════════════════ */}
      <Section id="contact" className="py-28 bg-white relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <SectionHeader
            badge="Get In Touch"
            badgeIcon={Mail}
            title="Let's Start a"
            titleHighlight="Conversation"
            subtitle="Have questions about SpeakEasy ASD? Want to learn how it can help your child? We'd love to hear from you."
          />
          
          <div className="grid lg:grid-cols-2 gap-12">
            {/* Form */}
            <motion.form
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              onSubmit={handleContactSubmit}
              className="space-y-6"
            >
              <div className="grid sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">Your Name</label>
                  <input name="name" type="text" required
                    className="w-full px-5 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all text-neutral-800 placeholder-neutral-400"
                    placeholder="John Doe" />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-neutral-700 mb-2">Email Address</label>
                  <input name="email" type="email" required
                    className="w-full px-5 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none transition-all text-neutral-800 placeholder-neutral-400"
                    placeholder="you@example.com" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-semibold text-neutral-700 mb-2">Your Message</label>
                <textarea name="message" required rows={6}
                  className="w-full px-5 py-4 border-2 border-neutral-200 rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 outline-none resize-none transition-all text-neutral-800 placeholder-neutral-400"
                  placeholder="Tell us about your child, questions about therapy, or anything else..." />
              </div>
              <button type="submit" className="btn-primary w-full text-lg">
                <Send className="w-5 h-5 mr-2" />
                Send Message
              </button>
            </motion.form>
            
            {/* Info */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="space-y-6"
            >
              <div className="bg-gradient-to-br from-primary-50 to-secondary-50 rounded-3xl p-8 border border-primary-100">
                <h3 className="text-xl font-bold text-neutral-900 mb-6">Contact Information</h3>
                <div className="space-y-5">
                  {[
                    { icon: MapPin, label: 'Address', value: 'Amrita Vishwa Vidyapeetham\nCoimbatore, Tamil Nadu, India', gradient: 'from-primary-500 to-indigo-600' },
                    { icon: Mail, label: 'Email', value: 'speakeasy@amrita.edu', gradient: 'from-purple-500 to-pink-600' },
                    { icon: Phone, label: 'Phone', value: '+91 422 268 5000', gradient: 'from-emerald-500 to-teal-600' },
                  ].map((item, idx) => (
                    <div key={idx} className="flex items-start gap-4">
                      <div className={`w-12 h-12 bg-gradient-to-br ${item.gradient} rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg`}>
                        <item.icon className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="font-semibold text-neutral-900 text-sm">{item.label}</p>
                        <p className="text-neutral-600 text-sm whitespace-pre-line">{item.value}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-3xl p-8 border border-amber-100">
                <h4 className="font-bold text-neutral-900 mb-4 flex items-center gap-2">
                  <Clock className="w-5 h-5 text-amber-600" />
                  Office Hours
                </h4>
                <div className="space-y-2 text-sm text-neutral-600">
                  <div className="flex justify-between"><span className="font-medium">Monday – Friday</span><span>9:00 AM – 6:00 PM</span></div>
                  <div className="flex justify-between"><span className="font-medium">Saturday</span><span>10:00 AM – 4:00 PM</span></div>
                  <div className="flex justify-between"><span className="font-medium">Sunday</span><span className="text-red-500">Closed</span></div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </Section>

      {/* ═══════════════════════════════════════════
          12. NEWSLETTER CTA BANNER
      ═══════════════════════════════════════════ */}
      <section className="relative py-24 bg-gradient-to-r from-primary-600 via-primary-500 to-secondary-600 overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-5" />
        <FloatingParticles />
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
              Ready to Transform Your Child's <span className="text-secondary-200">Speech Journey</span>?
            </h2>
            <p className="text-lg text-white/80 mb-10 max-w-2xl mx-auto">
              Join thousands of families using AI-powered therapy. Create your free account today and give your child the gift of confident communication.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button onClick={() => navigate('/register')} className="px-10 py-4 bg-white text-primary-700 rounded-2xl font-bold text-lg shadow-xl hover:shadow-2xl hover:scale-105 transition-all duration-300 flex items-center justify-center gap-2">
                Create Free Account
                <ArrowRight className="w-5 h-5" />
              </button>
              <button onClick={() => navigate('/login')} className="px-10 py-4 border-2 border-white/30 hover:border-white/60 text-white rounded-2xl font-bold text-lg hover:bg-white/10 transition-all duration-300">
                Sign In
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          13. PREMIUM FOOTER
      ═══════════════════════════════════════════ */}
      <footer className="bg-neutral-950 text-white relative overflow-hidden">
        {/* Wave separator */}
        <div className="absolute top-0 left-0 right-0 overflow-hidden leading-[0]">
          <svg viewBox="0 0 1200 120" className="relative block w-full h-16" preserveAspectRatio="none">
            <path d="M321.39,56.44c58-10.79,114.16-30.13,172-41.86,82.39-16.72,168.19-17.73,250.45-.39C823.78,31,906.67,72,985.66,92.83c70.05,18.48,146.53,26.09,214.34,3V0H0V27.35A600.21,600.21,0,0,0,321.39,56.44Z" fill="rgba(255,255,255,0.03)" />
          </svg>
        </div>
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-12">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-12 mb-16">
            {/* Brand */}
            <div className="lg:col-span-1">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-2xl flex items-center justify-center shadow-lg">
                  <span className="text-white font-bold text-xl">SE</span>
                </div>
                <div>
                  <div className="font-bold text-xl">SpeakEasy ASD</div>
                  <div className="text-[11px] text-neutral-500 font-medium tracking-wider uppercase">AI Speech Therapy</div>
                </div>
              </div>
              <p className="text-neutral-400 mb-6 leading-relaxed text-sm">
                Every child has a voice. We're here to help find it through innovative AI-powered speech therapy designed specifically for children with Autism Spectrum Disorder.
              </p>
              <p className="text-neutral-400 mb-6 text-sm italic">
                "Every voice matters. Every sound is progress." 🌟
              </p>
            </div>
            
            {/* Quick Links */}
            <div>
              <h4 className="font-bold text-lg mb-6">Quick Links</h4>
              <ul className="space-y-3">
                {navLinks.map((link) => (
                  <li key={link.to}>
                    <ScrollLink to={link.to} smooth={true} duration={600} offset={-80}
                      className="text-neutral-400 hover:text-primary-400 transition cursor-pointer text-sm flex items-center gap-2">
                      <ChevronRight className="w-3 h-3" />
                      {link.name}
                    </ScrollLink>
                  </li>
                ))}
              </ul>
            </div>
            
            {/* Resources */}
            <div>
              <h4 className="font-bold text-lg mb-6">Resources</h4>
              <ul className="space-y-3 text-neutral-400 text-sm">
                {[
                  { label: 'Documentation', path: '/help' },
                  { label: 'Support Center', path: '/help#contact-support' },
                  { label: 'Research & Privacy', path: '/about#privacy' },
                  { label: 'Privacy Policy', path: '/about#privacy' },
                  { label: 'Terms of Service', path: '/about#terms' },
                ].map((item) => (
                  <li key={item.label}>
                    <RouterLink to={item.path} className="hover:text-primary-400 transition flex items-center gap-2">
                      <ChevronRight className="w-3 h-3" />
                      {item.label}
                    </RouterLink>
                  </li>
                ))}
              </ul>
            </div>
            
            {/* Contact */}
            <div>
              <h4 className="font-bold text-lg mb-6">Get In Touch</h4>
              <div className="space-y-4 text-sm text-neutral-400">
                <div className="flex items-start gap-3">
                  <MapPin className="w-4 h-4 mt-1 text-primary-400 flex-shrink-0" />
                  <span>Amrita Vishwa Vidyapeetham<br/>Coimbatore, Tamil Nadu</span>
                </div>
                <div className="flex items-center gap-3">
                  <Mail className="w-4 h-4 text-primary-400 flex-shrink-0" />
                  <span>speakeasy@amrita.edu</span>
                </div>
                <div className="flex items-center gap-3">
                  <Phone className="w-4 h-4 text-primary-400 flex-shrink-0" />
                  <span>+91 422 268 5000</span>
                </div>
              </div>
              
              {/* SDG Badges */}
              <div className="mt-6">
                <p className="text-xs text-neutral-500 mb-3 font-semibold uppercase tracking-wider">SDG Aligned</p>
                <div className="flex gap-2">
                  {[3, 4, 9, 10].map((n) => (
                    <div key={n} className="w-10 h-10 bg-neutral-800 rounded-lg flex items-center justify-center text-xs font-bold text-primary-400 hover:bg-primary-600 hover:text-white transition-all cursor-default">
                      {n}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
          
          {/* Bottom bar */}
          <div className="border-t border-neutral-800 pt-8">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4">
              <p className="text-neutral-500 text-sm">
                © {new Date().getFullYear()} SpeakEasy ASD — Team 96 | Amrita Vishwa Vidyapeetham. All rights reserved.
              </p>
              <p className="text-neutral-500 text-sm flex items-center gap-1">
                Made with <Heart className="w-3.5 h-3.5 text-red-500 fill-red-500" /> for children with ASD
              </p>
            </div>
          </div>
        </div>
      </footer>

      {/* ═══════════════════════════════════════════
          14. BACK TO TOP BUTTON
      ═══════════════════════════════════════════ */}
      <AnimatePresence>
        {showBackToTop && (
          <motion.button
            initial={{ opacity: 0, y: 20, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.8 }}
            onClick={scrollToTop}
            className="fixed bottom-8 right-8 z-50 w-12 h-12 bg-gradient-to-br from-primary-600 to-secondary-600 text-white rounded-2xl shadow-xl hover:shadow-2xl flex items-center justify-center hover:scale-110 transition-transform"
          >
            <ArrowUp className="w-5 h-5" />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  )
}
