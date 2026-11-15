import { Component, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { supportsWebGL } from '../../features/characters/webglSupport'

const MOOD_LABELS = {
  idle: 'ready',
  speaking: 'speaking',
  listening: 'listening',
  thinking: 'thinking',
  encourage: 'encouraging you',
  celebrate: 'celebrating',
}

class CharacterCanvasBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

function useCharacterMotion(groupRef, headRef, mouthRef, { mood, audioLevel, motionLevel }) {
  useFrame(({ clock }, delta) => {
    const group = groupRef.current
    const head = headRef.current
    const mouth = mouthRef.current
    if (!group || !head || !mouth) return
    const time = clock.getElapsedTime()
    const motion = motionLevel === 'minimal' ? 0 : motionLevel === 'reduced' ? 0.32 : 1
    const celebration = mood === 'celebrate' ? Math.abs(Math.sin(time * 4.5)) * 0.15 : 0
    const listeningTilt = mood === 'listening' ? 0.13 : 0
    const thinkingTilt = mood === 'thinking' ? -0.11 : 0
    const targetY = -0.12 + motion * (Math.sin(time * 1.8) * 0.025 + celebration)
    group.position.y = THREE.MathUtils.damp(group.position.y, targetY, 7, delta)
    group.rotation.y = THREE.MathUtils.damp(group.rotation.y, motion * Math.sin(time * 0.75) * 0.06, 5, delta)
    head.rotation.z = THREE.MathUtils.damp(head.rotation.z, motion * (listeningTilt + thinkingTilt), 8, delta)
    const speakingAmount = mood === 'speaking'
      ? 0.45 + Math.abs(Math.sin(time * 11)) * 0.9
      : Math.min(1, Math.max(0, Number(audioLevel) || 0)) * 0.8 + 0.18
    mouth.scale.y = THREE.MathUtils.damp(mouth.scale.y, speakingAmount, 14, delta)
  })
}

function Eye({ position }) {
  return (
    <group position={position}>
      <mesh><sphereGeometry args={[0.105, 20, 16]} /><meshStandardMaterial color="#fffdf5" /></mesh>
      <mesh position={[0, 0, 0.09]}><sphereGeometry args={[0.048, 16, 12]} /><meshStandardMaterial color="#172554" /></mesh>
      <mesh position={[-0.014, 0.018, 0.132]}><sphereGeometry args={[0.012, 10, 8]} /><meshBasicMaterial color="#ffffff" /></mesh>
    </group>
  )
}

function KittenModel({ mood, audioLevel, motionLevel }) {
  const groupRef = useRef()
  const headRef = useRef()
  const mouthRef = useRef()
  useCharacterMotion(groupRef, headRef, mouthRef, { mood, audioLevel, motionLevel })
  return (
    <group ref={groupRef} position={[0, -0.12, 0]}>
      <mesh position={[0, -0.62, 0]} scale={[0.76, 0.9, 0.62]}>
        <sphereGeometry args={[0.72, 32, 24]} /><meshStandardMaterial color="#f59e45" roughness={0.72} />
      </mesh>
      <mesh position={[-0.48, -1.02, 0.08]} scale={[0.28, 0.42, 0.3]}>
        <sphereGeometry args={[0.55, 20, 16]} /><meshStandardMaterial color="#f7b267" />
      </mesh>
      <mesh position={[0.48, -1.02, 0.08]} scale={[0.28, 0.42, 0.3]}>
        <sphereGeometry args={[0.55, 20, 16]} /><meshStandardMaterial color="#f7b267" />
      </mesh>
      <mesh position={[0.66, -0.68, -0.1]} rotation={[0.2, 0.15, -0.55]}>
        <torusGeometry args={[0.48, 0.09, 14, 40, 4.2]} /><meshStandardMaterial color="#e88732" />
      </mesh>
      <group ref={headRef} position={[0, 0.18, 0.12]}>
        <mesh scale={[0.94, 0.84, 0.78]}>
          <sphereGeometry args={[0.72, 32, 24]} /><meshStandardMaterial color="#f6a04d" roughness={0.68} />
        </mesh>
        <mesh position={[-0.42, 0.53, -0.02]} rotation={[0.04, 0.03, -0.25]}>
          <coneGeometry args={[0.3, 0.66, 4]} /><meshStandardMaterial color="#e88732" />
        </mesh>
        <mesh position={[0.42, 0.53, -0.02]} rotation={[0.04, -0.03, 0.25]}>
          <coneGeometry args={[0.3, 0.66, 4]} /><meshStandardMaterial color="#e88732" />
        </mesh>
        <Eye position={[-0.25, 0.12, 0.6]} /><Eye position={[0.25, 0.12, 0.6]} />
        <mesh position={[0, -0.08, 0.72]} rotation={[Math.PI / 2, 0, 0]}>
          <coneGeometry args={[0.075, 0.1, 3]} /><meshStandardMaterial color="#ef7c8e" />
        </mesh>
        <mesh ref={mouthRef} position={[0, -0.28, 0.7]} scale={[1, 0.2, 1]}>
          <sphereGeometry args={[0.105, 20, 12]} /><meshStandardMaterial color="#7f1d1d" />
        </mesh>
        <mesh position={[0, -0.49, 0.38]} scale={[0.74, 0.13, 0.66]}>
          <torusGeometry args={[0.48, 0.09, 12, 36]} /><meshStandardMaterial color="#2563eb" metalness={0.08} />
        </mesh>
        <mesh position={[0.08, -0.62, 0.72]} rotation={[0.1, 0, -0.18]} scale={[0.22, 0.32, 0.08]}>
          <sphereGeometry args={[0.5, 20, 14]} /><meshStandardMaterial color="#60a5fa" />
        </mesh>
      </group>
    </group>
  )
}

function ElephantModel({ mood, audioLevel, motionLevel }) {
  const groupRef = useRef()
  const headRef = useRef()
  const mouthRef = useRef()
  useCharacterMotion(groupRef, headRef, mouthRef, { mood, audioLevel, motionLevel })
  return (
    <group ref={groupRef} position={[0, -0.12, 0]}>
      <mesh position={[0, -0.66, -0.04]} scale={[0.9, 0.86, 0.72]}>
        <sphereGeometry args={[0.72, 32, 24]} /><meshStandardMaterial color="#8fa9c7" roughness={0.82} />
      </mesh>
      {[-0.48, 0.48].map((x) => (
        <mesh key={x} position={[x, -1.13, 0.05]} scale={[0.34, 0.48, 0.34]}>
          <sphereGeometry args={[0.52, 20, 16]} /><meshStandardMaterial color="#829dbd" />
        </mesh>
      ))}
      <group ref={headRef} position={[0, 0.14, 0.18]}>
        {[-1, 1].map((side) => (
          <mesh key={side} position={[side * 0.63, 0.02, -0.02]} scale={[0.22, 0.72, 0.55]}>
            <sphereGeometry args={[0.78, 24, 18]} /><meshStandardMaterial color="#9bb4d0" side={THREE.DoubleSide} />
          </mesh>
        ))}
        <mesh scale={[0.9, 0.82, 0.76]}>
          <sphereGeometry args={[0.72, 32, 24]} /><meshStandardMaterial color="#91abc8" roughness={0.8} />
        </mesh>
        <Eye position={[-0.24, 0.13, 0.58]} /><Eye position={[0.24, 0.13, 0.58]} />
        <mesh position={[0, -0.32, 0.68]} rotation={[0.12, 0, 0]} scale={[0.23, 0.78, 0.23]}>
          <capsuleGeometry args={[0.18, 0.58, 8, 18]} /><meshStandardMaterial color="#829fbe" />
        </mesh>
        <mesh ref={mouthRef} position={[0, -0.2, 0.7]} scale={[1, 0.18, 1]}>
          <sphereGeometry args={[0.095, 18, 12]} /><meshStandardMaterial color="#713f5c" />
        </mesh>
        <mesh position={[0, -0.48, 0.3]} scale={[0.78, 0.13, 0.68]}>
          <torusGeometry args={[0.48, 0.09, 12, 36]} /><meshStandardMaterial color="#14b8a6" />
        </mesh>
      </group>
    </group>
  )
}

function CharacterWorld(props) {
  return (
    <>
      <ambientLight intensity={1.15} />
      <directionalLight position={[3, 5, 4]} intensity={1.7} castShadow />
      <pointLight position={[-3, 1, 3]} intensity={0.8} color="#c4b5fd" />
      {props.character === 'kavi' ? <ElephantModel {...props} /> : <KittenModel {...props} />}
      <mesh position={[0, -1.48, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[1.5, 48]} /><meshStandardMaterial color={props.character === 'kavi' ? '#ccfbf1' : '#fef3c7'} transparent opacity={0.76} />
      </mesh>
    </>
  )
}

function CharacterFallback({ character, fallbackImage }) {
  return (
    <div className="character-stage__fallback" data-character-fallback="true">
      {fallbackImage ? <img src={fallbackImage} alt="" /> : <span aria-hidden="true">{character === 'kavi' ? '🐘' : '🐱'}</span>}
    </div>
  )
}

export default function CharacterStage3D({
  character = 'pippin',
  mood = 'idle',
  message = '',
  audioLevel = 0,
  motionLevel = 'full',
  fallbackImage = '',
  forceFallback = false,
  className = '',
}) {
  const name = character === 'kavi' ? 'Kavi' : 'Pippin'
  const canRender3D = supportsWebGL({ forceFallback })
  const fallback = <CharacterFallback character={character} fallbackImage={fallbackImage} />
  return (
    <div
      className={`character-stage character-stage--${character} character-stage--${mood} ${className}`.trim()}
      role="img"
      aria-label={`${name} is ${MOOD_LABELS[mood] || 'ready'}. ${message}`.trim()}
      data-testid={`character-stage-${character}`}
      data-renderer={canRender3D ? 'webgl' : 'fallback'}
      data-mood={mood}
    >
      <span className="character-stage__status">{name} is {MOOD_LABELS[mood] || 'ready'}.</span>
      {canRender3D ? (
        <CharacterCanvasBoundary fallback={fallback}>
          <Canvas
            aria-hidden="true"
            camera={{ position: [0, -0.08, 4.35], fov: 39 }}
            dpr={[1, 1.5]}
            gl={{ antialias: true, alpha: true, powerPreference: 'low-power' }}
            shadows={motionLevel === 'full'}
          >
            <CharacterWorld character={character} mood={mood} audioLevel={audioLevel} motionLevel={motionLevel} />
          </Canvas>
        </CharacterCanvasBoundary>
      ) : fallback}
    </div>
  )
}
