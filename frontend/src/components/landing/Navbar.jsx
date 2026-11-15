import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import { Link } from 'react-scroll'
import { useAuthStore } from '../../store/authStore'
import { useNavigate } from 'react-router-dom'

export default function Navbar({ onLoginClick, onRegisterClick, onAdminClick }) {
  const [isScrolled, setIsScrolled] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const { isAuthenticated, user } = useAuthStore()
  const navigate = useNavigate()
  
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50)
    }
    
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])
  
  const navItems = [
    { name: 'Home', to: 'home' },
    { name: 'Features', to: 'features' },
    { name: 'How It Works', to: 'how-it-works' },
    { name: 'About', to: 'about' },
    { name: 'Contact', to: 'contact' },
  ]
  
  return (
    <motion.nav
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className={`fixed top-0 left-0 right-0 z-40 transition-all duration-300 ${
        isScrolled ? 'bg-white/90 backdrop-blur-lg shadow-lg' : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-gradient-to-br from-primary to-secondary rounded-full flex items-center justify-center text-white font-bold text-xl shadow-lg">
              SE
            </div>
            <span className="font-bold text-xl text-primary">SpeakEasy ASD</span>
          </div>
          
          {/* Desktop Menu */}
          <div className="hidden md:flex items-center space-x-8">
            {navItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                spy={true}
                smooth={true}
                duration={500}
                className="text-gray-700 hover:text-primary transition cursor-pointer font-medium"
              >
                {item.name}
              </Link>
            ))}
          </div>
          
          {/* Auth Buttons */}
          <div className="hidden md:flex items-center space-x-4">
            {isAuthenticated ? (
              <>
                <button
                  onClick={() => navigate(user.role === 'admin' ? '/admin' : '/dashboard')}
                  className="px-6 py-2 bg-gradient-to-r from-primary to-secondary text-white rounded-full hover:from-primary-dark hover:to-secondary-dark transition font-semibold shadow-md"
                >
                  Dashboard
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={onLoginClick}
                  className="px-6 py-2 border-2 border-primary text-primary rounded-full hover:bg-primary hover:text-white transition font-semibold"
                >
                  Login
                </button>
                <button
                  onClick={onRegisterClick}
                  className="px-6 py-2 bg-gradient-to-r from-primary to-secondary text-white rounded-full hover:from-primary-dark hover:to-secondary-dark transition font-semibold shadow-md"
                >
                  Get Started
                </button>
                <button
                  onClick={onAdminClick}
                  className="px-4 py-2 text-sm text-neutral-600 hover:text-primary transition"
                >
                  Admin
                </button>
              </>
            )}
          </div>
          
          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-gray-100"
          >
            {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
        
        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden pb-4"
          >
            <div className="flex flex-col space-y-4">
              {navItems.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  spy={true}
                  smooth={true}
                  duration={500}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="text-gray-700 hover:text-primary transition cursor-pointer font-medium"
                >
                  {item.name}
                </Link>
              ))}
              
              {!isAuthenticated && (
                <div className="flex flex-col space-y-2 pt-4 border-t">
                  <button
                    onClick={() => {
                      onLoginClick()
                      setIsMobileMenuOpen(false)
                    }}
                    className="w-full px-6 py-2 border-2 border-primary text-primary rounded-full hover:bg-primary hover:text-white transition font-semibold"
                  >
                    Login
                  </button>
                  <button
                    onClick={() => {
                      onRegisterClick()
                      setIsMobileMenuOpen(false)
                    }}
                    className="w-full px-6 py-2 bg-gradient-to-r from-primary to-secondary text-white rounded-full hover:from-primary-dark hover:to-secondary-dark transition font-semibold shadow-md"
                  >
                    Get Started
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </motion.nav>
  )
}
