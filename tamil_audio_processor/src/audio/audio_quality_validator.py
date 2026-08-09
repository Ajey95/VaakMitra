import numpy as np

class AudioQualityValidator:
    def __init__(self, min_duration_sec=0.2, max_clipping_ratio=0.05, silence_threshold=1e-5):
        """
        Validator to reject poor quality audio without penalizing pronunciation.
        """
        self.min_duration_sec = min_duration_sec
        self.max_clipping_ratio = max_clipping_ratio
        self.silence_threshold = silence_threshold
        
    def validate(self, audio: np.ndarray, sample_rate: int = 16000) -> dict:
        """
        Validates audio quality.
        Returns a dict with 'valid' bool and a neutral 'reason'.
        """
        if len(audio) == 0:
            return {"valid": False, "reason": "empty"}
            
        duration = len(audio) / sample_rate
        if duration < self.min_duration_sec:
            return {"valid": False, "reason": "too_short"}
            
        # Check silence
        energy = np.mean(audio**2)
        if energy < self.silence_threshold:
            return {"valid": False, "reason": "silent"}
            
        # Check clipping (values near 1.0 or -1.0)
        clipped_samples = np.sum(np.abs(audio) >= 0.99)
        clipping_ratio = clipped_samples / len(audio)
        if clipping_ratio > self.max_clipping_ratio:
            return {"valid": False, "reason": "clipped"}
            
        return {"valid": True, "reason": "valid"}
