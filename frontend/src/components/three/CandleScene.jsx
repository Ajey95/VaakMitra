import { useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { motion } from 'framer-motion'

function Candle({ airflowScore, onExtinguish }) {
  const flameRef = useRef()
  const candleRef = useRef()
  const lightRef = useRef()
  const smokeRef = useRef()
  
  const isExtinguished = airflowScore > 0.6
  
  useFrame((state) => {
    const time = state.clock.getElapsedTime()
    
    if (flameRef.current && !isExtinguished) {
      // Flicker effect
      const flicker = Math.sin(time * 8) * 0.1
      flameRef.current.scale.y = 1 + flicker
      
      // Bend based on airflow
      flameRef.current.rotation.z = airflowScore * 0.5
      
      // Light intensity flicker
      if (lightRef.current) {
        lightRef.current.intensity = 2 + flicker
      }
    }
    
    // Handle extinguish animation
    if (isExtinguished && flameRef.current && flameRef.current.scale.y > 0.01) {
      flameRef.current.scale.y *= 0.95
      
      if (flameRef.current.scale.y < 0.1 && onExtinguish) {
        onExtinguish()
      }
      
      // Emit smoke particles
      if (smokeRef.current) {
        smokeRef.current.position.y += 0.05
        smokeRef.current.material.opacity *= 0.98
      }
    }
  })
  
  return (
    <group>
      {/* Candle body */}
      <mesh ref={candleRef} position={[0, 0, 0]} castShadow>
        <cylinderGeometry args={[0.3, 0.4, 3, 32]} />
        <meshStandardMaterial color="#FFF5E1" />
      </mesh>
      
      {/* Wax drip */}
      <mesh position={[0.35, -0.5, 0]}>
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshStandardMaterial color="#FFF0D1" />
      </mesh>
      
      {/* Wick */}
      <mesh position={[0, 1.5, 0]}>
        <cylinderGeometry args={[0.02, 0.02, 0.3, 8]} />
        <meshStandardMaterial color="#2D2D2D" />
      </mesh>
      
      {/* Flame */}
      {!isExtinguished && (
        <group ref={flameRef} position={[0, 1.8, 0]}>
          <mesh>
            <coneGeometry args={[0.15, 0.5, 8]} />
            <meshStandardMaterial
              color="#FFA500"
              emissive="#FF6600"
              emissiveIntensity={2}
              transparent
              opacity={0.9}
            />
          </mesh>
          
          {/* Inner flame */}
          <mesh position={[0, 0.1, 0]}>
            <coneGeometry args={[0.1, 0.3, 8]} />
            <meshStandardMaterial
              color="#FFFF00"
              emissive="#FFAA00"
              emissiveIntensity={3}
              transparent
              opacity={0.8}
            />
          </mesh>
          
          {/* Point light inside flame */}
          <pointLight
            ref={lightRef}
            color="#FFA500"
            intensity={2}
            distance={3}
            position={[0, 0.2, 0]}
          />
        </group>
      )}
      
      {/* Smoke (appears when extinguishing) */}
      {isExtinguished && (
        <mesh ref={smokeRef} position={[0, 2, 0]}>
          <sphereGeometry args={[0.2, 16, 16]} />
          <meshBasicMaterial
            color="#888888"
            transparent
            opacity={0.5}
          />
        </mesh>
      )}
    </group>
  )
}

export default function CandleScene({ airflowScore, word }) {
  const [extinguished, setExtinguished] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  
  const handleExtinguish = () => {
    if (word === 'appa' && !extinguished) {
      setExtinguished(true)
      setShowSuccess(true)
    }
  }
  
  return (
    <div className="relative w-full h-[600px]">
      <Canvas
        camera={{ position: [0, 2, 5], fov: 50 }}
        shadows
      >
        <ambientLight intensity={0.4} color="#FFFFFF" />
        <directionalLight
          position={[5, 5, 5]}
          intensity={0.5}
          castShadow
        />
        
        <Candle airflowScore={airflowScore} onExtinguish={handleExtinguish} />
        
        {/* Floor */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.5, 0]} receiveShadow>
          <planeGeometry args={[10, 10]} />
          <shadowMaterial opacity={0.3} />
        </mesh>
      </Canvas>
      
      {/* Airflow meter */}
      <div className="absolute left-8 top-1/2 -translate-y-1/2">
        <div className="w-12 bg-gray-200 rounded-full h-64 overflow-hidden">
          <motion.div
            className="w-full bg-gradient-to-t from-blue-500 via-orange-500 to-red-500 rounded-full"
            initial={{ height: 0 }}
            animate={{ height: `${airflowScore * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
        <p className="text-center mt-2 text-sm font-semibold">
          Airflow<br />{Math.round(airflowScore * 100)}%
        </p>
      </div>
      
      {/* Success overlay */}
      {showSuccess && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm"
        >
          <div className="bg-white rounded-3xl p-12 text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring" }}
              className="text-8xl mb-4"
            >
              🎉
            </motion.div>
            <h3 className="text-3xl font-bold text-primary mb-2">Perfect!</h3>
            <p className="text-xl text-gray-600">Great airflow for "appa"!</p>
          </div>
        </motion.div>
      )}
    </div>
  )
}
