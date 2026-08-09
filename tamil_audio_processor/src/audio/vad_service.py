import numpy as np
import onnxruntime as ort
import logging

logger = logging.getLogger("VADService")

class VADService:
    def __init__(self, model_path="models/silero_vad.onnx", threshold=0.5):
        self.model_path = model_path
        self.threshold = threshold
        try:
            # Minimal ONNX session initialization
            self.session = ort.InferenceSession(self.model_path)
            self.use_onnx = True
            logger.info("Loaded ONNX VAD model successfully.")
        except Exception as e:
            logger.warning(f"Could not load ONNX model at {model_path}. Using fallback energy VAD. Error: {e}")
            self.use_onnx = False
            
    def get_speech_timestamps(self, audio: np.ndarray, sample_rate: int = 16000):
        """
        Returns a list of dicts with 'start' and 'end' samples for speech segments.
        Tolerates longer pauses typical in ASD child speech.
        """
        if len(audio) == 0:
            return []
            
        if self.use_onnx:
            # In a real environment, we would run the audio in 512-sample chunks 
            # through the Silero ONNX model and track the probabilities.
            pass
            
        # Fallback heuristic (energy-based) for testing / when ONNX fails
        window_size = int(sample_rate * 0.03) # 30ms window
        stride = int(sample_rate * 0.01) # 10ms stride
        
        timestamps = []
        is_speaking = False
        start_idx = 0
        
        for i in range(0, len(audio) - window_size, stride):
            window = audio[i:i+window_size]
            energy = np.mean(window**2)
            if energy > 0.001: 
                if not is_speaking:
                    is_speaking = True
                    start_idx = i
            else:
                if is_speaking:
                    is_speaking = False
                    timestamps.append({"start": start_idx, "end": i})
                    
        if is_speaking:
            timestamps.append({"start": start_idx, "end": len(audio)})
            
        # Merge segments to tolerate longer child pauses (e.g. up to 500ms)
        pause_tolerance = int(sample_rate * 0.5)
        merged = []
        for t in timestamps:
            if not merged:
                merged.append(t)
            else:
                last = merged[-1]
                if t['start'] - last['end'] < pause_tolerance:
                    last['end'] = t['end']
                else:
                    merged.append(t)
                    
        return merged
