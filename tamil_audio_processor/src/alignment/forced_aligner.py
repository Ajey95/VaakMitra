import numpy as np
import logging

logger = logging.getLogger("ForcedAligner")

class CTCForcedAligner:
    def __init__(self, blank_idx=0):
        self.blank_idx = blank_idx
        
    def align(self, expected_phonemes: list, log_probs: np.ndarray, frame_duration_ms: float = 20.0) -> dict:
        """
        Performs Viterbi decoding to align expected phonemes to CTC log probabilities.
        
        :param expected_phonemes: List of expected phonemes (strings).
        :param log_probs: 2D array [frames, num_classes] of log probabilities (from Member 2).
        :param frame_duration_ms: Duration of each frame in milliseconds.
        :return: Dictionary containing phoneme alignments and overall confidence.
        """
        # Note: A production implementation requires mapping `expected_phonemes` to 
        # vocabulary indices used by Member 2. We mock the alignment math here.
        
        num_frames = log_probs.shape[0]
        num_expected = len(expected_phonemes)
        
        if num_frames == 0 or num_expected == 0:
            logger.warning("Empty frames or expected phonemes provided.")
            return {"phoneme_alignment": [], "alignment_confidence": 0.0}
            
        # Simplified Mock Viterbi logic
        alignments = []
        frame_step = num_frames / num_expected
        
        overall_conf = 0.0
        
        for i, p in enumerate(expected_phonemes):
            start_frame = int(i * frame_step)
            end_frame = int((i + 1) * frame_step)
            
            # Simulated confidence based on local window
            window_probs = log_probs[start_frame:end_frame]
            conf = float(np.mean(np.max(np.exp(window_probs), axis=1))) if len(window_probs) > 0 else 0.0
            
            overall_conf += conf
            
            alignments.append({
                "phoneme": p,
                "start_ms": start_frame * frame_duration_ms,
                "end_ms": end_frame * frame_duration_ms,
                "confidence": round(conf, 2)
            })
            
        overall_conf /= num_expected
        
        return {
            "phoneme_alignment": alignments,
            "alignment_confidence": round(overall_conf, 2)
        }
