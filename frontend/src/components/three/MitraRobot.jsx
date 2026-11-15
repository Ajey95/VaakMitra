/**
 * MitraRobot.jsx
 * ──────────────────────────────────────────────────────────────────
 * The MITRA 3D robot companion powered by /mitra_robot.gltf.
 * 
 * Props (all optional):
 *   mood        'idle' | 'happy' | 'celebrate' | 'encourage' | 'listen' | 'thinking'
 *   audioLevel  0–1  (microphone amplitude — drives mouth/head bob)
 *   size        number (canvas height in px, default 400)
 *   showBubble  bool (show speech bubble with message)
 *   message     string (text shown in speech bubble)
 *   autoRotate  bool
 *   className   string
 * ──────────────────────────────────────────────────────────────────
 */

import { useRef, useState, useEffect, Suspense } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import {
  useGLTF,
  OrbitControls,
  Stage,
  Float,
  Html,
  ContactShadows,
  Environment,
} from '@react-three/drei'
import { motion, AnimatePresence } from 'framer-motion'
import * as THREE from 'three'

// ── Mood config ────────────────────────────────────────────────────
const MOOD_CONFIG = {
  idle: {
    floatSpeed: 1.2,
    floatIntensity: 0.4,
    rotationRange: 0.08,
    bobAmplitude: 0.05,
    color: '#6366f1',
    emoji: '🤖',
    glowColor: '#818cf8',
  },
  happy: {
    floatSpeed: 2.5,
    floatIntensity: 0.8,
    rotationRange: 0.18,
    bobAmplitude: 0.12,
    color: '#f59e0b',
    emoji: '😊',
    glowColor: '#fcd34d',
  },
  celebrate: {
    floatSpeed: 4,
    floatIntensity: 1.2,
    rotationRange: 0.35,
    bobAmplitude: 0.2,
    color: '#10b981',
    emoji: '🎉',
    glowColor: '#34d399',
  },
  encourage: {
    floatSpeed: 1.8,
    floatIntensity: 0.6,
    rotationRange: 0.12,
    bobAmplitude: 0.08,
    color: '#3b82f6',
    emoji: '💪',
    glowColor: '#93c5fd',
  },
  listen: {
    floatSpeed: 0.8,
    floatIntensity: 0.3,
    rotationRange: 0.05,
    bobAmplitude: 0.03,
    color: '#8b5cf6',
    emoji: '👂',
    glowColor: '#c4b5fd',
  },
  thinking: {
    floatSpeed: 1.0,
    floatIntensity: 0.35,
    rotationRange: 0.06,
    bobAmplitude: 0.04,
    color: '#06b6d4',
    emoji: '🤔',
    glowColor: '#67e8f9',
  },
}

// ── Inner robot mesh ───────────────────────────────────────────────
function RobotModel({ mood = 'idle', audioLevel = 0 }) {
  const groupRef = useRef()
  const { scene, animations } = useGLTF('/mitra_robot.gltf')
  const mixerRef = useRef()
  const clockRef = useRef(new THREE.Clock())
  const config = MOOD_CONFIG[mood] || MOOD_CONFIG.idle

  // Clone the scene so multiple instances don't share state
  const clonedScene = scene.clone(true)

  // Set up animation mixer if the GLTF has animations
  useEffect(() => {
    if (animations && animations.length > 0) {
      mixerRef.current = new THREE.AnimationMixer(clonedScene)
      // Play all clips (idle loop)
      animations.forEach((clip) => {
        const action = mixerRef.current.clipAction(clip)
        action.play()
      })
    }
    return () => {
      if (mixerRef.current) mixerRef.current.stopAllAction()
    }
  }, [animations, clonedScene])

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    const delta = clockRef.current.getDelta()

    if (groupRef.current) {
      // Gentle idle bob
      const bobSpeed = mood === 'celebrate' ? 6 : mood === 'happy' ? 3 : 1.5
      groupRef.current.position.y =
        Math.sin(t * bobSpeed) * config.bobAmplitude

      // Head tilt driven by audioLevel (mouth-sync effect)
      const audioInfluence = audioLevel * 0.15
      groupRef.current.rotation.x = Math.sin(t * 2) * 0.02 + audioInfluence

      // Celebrate: spin wiggle
      if (mood === 'celebrate') {
        groupRef.current.rotation.y = Math.sin(t * 4) * 0.3
        groupRef.current.rotation.z = Math.sin(t * 3) * 0.08
      } else if (mood === 'listen') {
        // Lean slightly forward when listening
        groupRef.current.rotation.x = -0.08 + Math.sin(t * 0.8) * 0.02 + audioInfluence
      } else {
        groupRef.current.rotation.y = Math.sin(t * 0.5) * config.rotationRange
        groupRef.current.rotation.z = Math.sin(t * 0.7) * 0.02
      }
    }

    // Advance animation mixer
    if (mixerRef.current) {
      const speed = mood === 'celebrate' ? 2.5 : mood === 'happy' ? 1.5 : 1
      mixerRef.current.update(delta * speed)
    }
  })

  return (
    <group ref={groupRef}>
      <primitive object={clonedScene} scale={1.8} />
    </group>
  )
}

// ── Orbit ring decoration ──────────────────────────────────────────
function OrbitRing({ color = '#818cf8', radius = 1.8, speed = 1, offset = 0 }) {
  const ringRef = useRef()
  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    if (ringRef.current) {
      ringRef.current.rotation.z = t * speed + offset
    }
  })
  return (
    <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[radius, 0.015, 16, 100]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} transparent opacity={0.35} />
    </mesh>
  )
}

// ── Particle stars ─────────────────────────────────────────────────
function CelebrationParticles({ active }) {
  const points = useRef()
  const count = 60

  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 4
    positions[i * 3 + 1] = Math.random() * 4
    positions[i * 3 + 2] = (Math.random() - 0.5) * 4
  }

  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    if (points.current && active) {
      points.current.rotation.y = t * 0.3
      points.current.material.opacity = 0.6 + Math.sin(t * 3) * 0.3
    }
  })

  if (!active) return null

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#fcd34d"
        size={0.06}
        transparent
        opacity={0.8}
        sizeAttenuation
      />
    </points>
  )
}

// ── Camera auto-fit ─────────────────────────────────────────────────
function AutoCamera({ zoom = 1 }) {
  const { camera } = useThree()
  useEffect(() => {
    camera.position.set(0, 0.5, 4 / zoom)
    camera.lookAt(0, 0, 0)
  }, [camera, zoom])
  return null
}

// ── Fallback spinner while GLTF loads ──────────────────────────────
function LoadingFallback() {
  const meshRef = useRef()
  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    if (meshRef.current) {
      meshRef.current.rotation.y = t * 2
      meshRef.current.rotation.x = t * 1.3
    }
  })
  return (
    <mesh ref={meshRef}>
      <octahedronGeometry args={[0.6, 0]} />
      <meshStandardMaterial color="#6366f1" emissive="#4338ca" emissiveIntensity={0.5} wireframe />
    </mesh>
  )
}

// ── Speech bubble overlay ──────────────────────────────────────────
function SpeechBubble({ message, mood }) {
  const config = MOOD_CONFIG[mood] || MOOD_CONFIG.idle
  const bubbleStyle = {
    background: 'rgba(255,255,255,0.96)',
    backdropFilter: 'blur(12px)',
    border: `2px solid ${config.glowColor}`,
    borderRadius: '20px',
    padding: '10px 16px',
    maxWidth: '200px',
    boxShadow: `0 8px 32px ${config.glowColor}44`,
    fontSize: '13px',
    fontWeight: '600',
    color: '#1e293b',
    lineHeight: '1.4',
    textAlign: 'center',
    position: 'relative',
  }
  const tailStyle = {
    position: 'absolute',
    bottom: '-10px',
    left: '50%',
    transform: 'translateX(-50%)',
    width: 0,
    height: 0,
    borderLeft: '10px solid transparent',
    borderRight: '10px solid transparent',
    borderTop: `10px solid ${config.glowColor}`,
  }
  return (
    <Html center position={[0, 2.6, 0]} style={{ pointerEvents: 'none' }}>
      <motion.div
        initial={{ opacity: 0, y: -10, scale: 0.8 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        style={bubbleStyle}
      >
        <span style={{ marginRight: '6px' }}>{config.emoji}</span>
        {message}
        <div style={tailStyle} />
      </motion.div>
    </Html>
  )
}

// ══════════════════════════════════════════════════════════════════
// MAIN EXPORTED COMPONENT
// ══════════════════════════════════════════════════════════════════
export default function MitraRobot({
  mood = 'idle',
  audioLevel = 0,
  size = 400,
  showBubble = false,
  message = '',
  autoRotate = false,
  className = '',
  zoom = 1,
}) {
  const config = MOOD_CONFIG[mood] || MOOD_CONFIG.idle
  const isCelebrating = mood === 'celebrate'

  return (
    <div
      className={`relative ${className}`}
      style={{ height: size, width: '100%' }}
    >
      {/* Glow halo behind canvas */}
      <div
        className="absolute inset-0 rounded-full pointer-events-none"
        style={{
          background: `radial-gradient(ellipse at center, ${config.glowColor}22 0%, transparent 70%)`,
          transition: 'background 0.8s ease',
        }}
      />

      <Canvas
        gl={{ antialias: true, alpha: true }}
        camera={{ position: [0, 0.5, 4], fov: 45 }}
        style={{ background: 'transparent' }}
      >
        <AutoCamera zoom={zoom} />

        {/* Lighting */}
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 8, 5]} intensity={1.2} castShadow />
        <pointLight position={[-3, 2, 3]} intensity={0.4} color={config.glowColor} />
        <pointLight position={[3, -1, -3]} intensity={0.2} color="#ffffff" />

        {/* Environment */}
        <Environment preset="city" />

        {/* Orbit decorations */}
        <OrbitRing color={config.glowColor} radius={1.5} speed={0.4} offset={0} />
        <OrbitRing color={config.color} radius={2.0} speed={-0.25} offset={Math.PI / 3} />

        {/* Celebration particles */}
        <CelebrationParticles active={isCelebrating} />

        {/* Contact shadow */}
        <ContactShadows
          opacity={0.3}
          scale={4}
          blur={1.5}
          far={3}
          resolution={256}
          color="#000000"
          position={[0, -1.6, 0]}
        />

        {/* The GLTF robot with Float wrapper */}
        <Float
          speed={config.floatSpeed}
          rotationIntensity={0}
          floatIntensity={config.floatIntensity}
        >
          <Suspense fallback={<LoadingFallback />}>
            <RobotModel mood={mood} audioLevel={audioLevel} />
            {showBubble && message && (
              <SpeechBubble message={message} mood={mood} />
            )}
          </Suspense>
        </Float>

        {/* Optional orbit controls */}
        {autoRotate && (
          <OrbitControls
            enableZoom={false}
            enablePan={false}
            autoRotate
            autoRotateSpeed={1.5}
            minPolarAngle={Math.PI / 3}
            maxPolarAngle={Math.PI / 1.8}
          />
        )}
      </Canvas>

      {/* Mood indicator dot */}
      <div
        className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold text-white shadow-lg"
        style={{
          background: `linear-gradient(135deg, ${config.color}, ${config.glowColor})`,
          transition: 'background 0.5s ease',
        }}
      >
        <span>{config.emoji}</span>
        <span className="capitalize">{mood === 'idle' ? 'MITRA' : mood.toUpperCase()}</span>
        {audioLevel > 0.1 && (
          <span className="flex gap-0.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="inline-block w-0.5 rounded-full bg-white"
                style={{
                  height: `${6 + audioLevel * 10 * (i + 1) * 0.4}px`,
                  opacity: audioLevel > i * 0.3 ? 1 : 0.3,
                  transition: 'height 0.1s',
                }}
              />
            ))}
          </span>
        )}
      </div>
    </div>
  )
}

// Pre-load the GLTF so there's no pop-in delay
useGLTF.preload('/mitra_robot.gltf')
