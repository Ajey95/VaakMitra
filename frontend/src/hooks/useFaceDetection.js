import { useState, useRef, useEffect, useCallback } from 'react'
import { measureMouthGeometry } from '../features/mouthMirror/mouthGeometry'

export const useFaceDetection = (videoRef, canvasRef) => {
  const [faceData, setFaceData] = useState({
    faceDetected: false,
    mouthWidth: 0,
    mouthHeight: 0,
    mouthOpenRatio: 0,
    mouthIsOpen: false
  })
  const [isProcessing, setIsProcessing] = useState(false)
  const faceMeshRef = useRef(null)
  const animationFrameRef = useRef(null)
  
  // Initialize MediaPipe Face Mesh
  useEffect(() => {
    if (typeof window !== 'undefined' && window.FaceMesh) {
      try {
        const faceMesh = new window.FaceMesh({
          locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619/${file}`
          }
        })
        
        faceMesh.setOptions({
          maxNumFaces: 1,
          refineLandmarks: true,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5
        })
        
        faceMesh.onResults(onResults)
        faceMeshRef.current = faceMesh
        
        console.log('✅ MediaPipe Face Mesh initialized')
      } catch (error) {
        console.warn('Face tracking is unavailable; speech practice will continue:', error)
      }
    }
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [])
  
  const onResults = useCallback((results) => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    
    if (!ctx || !canvas) return
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
      const landmarks = results.multiFaceLandmarks[0]
      
      // Draw landmarks
      ctx.fillStyle = '#4ECDC4'
      landmarks.forEach((landmark) => {
        ctx.beginPath()
        ctx.arc(
          landmark.x * canvas.width,
          landmark.y * canvas.height,
          2,
          0,
          2 * Math.PI
        )
        ctx.fill()
      })
      
      const geometry = measureMouthGeometry(landmarks)
      const upperLip = landmarks[13]
      const leftCorner = landmarks[61]
      const mouthHeight = (geometry?.mouthHeight || 0) * canvas.height
      const mouthWidth = (geometry?.mouthWidth || 0) * canvas.width
      const mouthOpenRatio = geometry?.mouthOpenRatio || 0
      const mouthIsOpen = mouthOpenRatio > 0.35
      
      // Draw mouth bounding box
      ctx.strokeStyle = mouthIsOpen ? '#FFE66D' : '#4ECDC4'
      ctx.lineWidth = 2
      ctx.strokeRect(
        leftCorner.x * canvas.width - 5,
        upperLip.y * canvas.height - 5,
        mouthWidth + 10,
        mouthHeight + 10
      )
      
      setFaceData({
        faceDetected: true,
        mouthWidth: geometry?.mouthWidth || 0,
        mouthHeight: geometry?.mouthHeight || 0,
        mouthOpenRatio,
        mouthIsOpen
      })
    } else {
      setFaceData({
        faceDetected: false,
        mouthWidth: 0,
        mouthHeight: 0,
        mouthOpenRatio: 0,
        mouthIsOpen: false
      })
    }
  }, [canvasRef])
  
  const processFrame = useCallback(async () => {
    if (!faceMeshRef.current || !videoRef.current || !isProcessing) {
      return
    }
    
    try {
      await faceMeshRef.current.send({ image: videoRef.current })
    } catch (error) {
      console.warn('Face tracking stopped; speech practice will continue:', error)
      setIsProcessing(false)
      setFaceData({
        faceDetected: false,
        mouthWidth: 0,
        mouthHeight: 0,
        mouthOpenRatio: 0,
        mouthIsOpen: false,
      })
      return
    }
    
    animationFrameRef.current = requestAnimationFrame(processFrame)
  }, [videoRef, isProcessing])
  
  const startDetection = useCallback(() => {
    setIsProcessing(true)
  }, [])
  
  const stopDetection = useCallback(() => {
    setIsProcessing(false)
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
    }
  }, [])
  
  useEffect(() => {
    if (isProcessing) {
      processFrame()
    }
  }, [isProcessing, processFrame])
  
  return {
    faceData,
    startDetection,
    stopDetection,
    isProcessing
  }
}
