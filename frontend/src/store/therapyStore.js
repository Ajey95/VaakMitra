import { create } from 'zustand'
import { lessonSlideSequence } from '../features/curriculum/lessonRoadmap'

export const useTherapyStore = create((set) => ({
  currentLesson: null,
  currentSlide: 1,
  sessionResults: [],
  
  setCurrentLesson: (lesson) => set({ currentLesson: lesson, currentSlide: 1 }),
  
  setCurrentSlide: (slide) => set({ currentSlide: slide }),
  
  nextSlide: () => set((state) => {
    const slides = lessonSlideSequence(state.currentLesson)
    const position = Math.max(0, slides.indexOf(state.currentSlide))
    return { currentSlide: slides[Math.min(position + 1, slides.length - 1)] }
  }),
  
  prevSlide: () => set((state) => {
    const slides = lessonSlideSequence(state.currentLesson)
    const position = Math.max(0, slides.indexOf(state.currentSlide))
    return { currentSlide: slides[Math.max(position - 1, 0)] }
  }),
  
  addSessionResult: (result) => set((state) => ({
    sessionResults: [...state.sessionResults, result]
  })),
  
  resetSession: () => set({ 
    currentLesson: null, 
    currentSlide: 1, 
    sessionResults: [] 
  })
}))
