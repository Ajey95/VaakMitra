"""Dynamic Time Warping alignment for syllable-level scoring."""
import numpy as np
try:
    from fastdtw import fastdtw
    from scipy.spatial.distance import euclidean
    DTW_AVAILABLE = True
except ImportError:
    DTW_AVAILABLE = False
    print("⚠️ fastdtw not available. Install with: pip install fastdtw scipy")

class SyllableAligner:
    """Uses DTW to temporally align atypical speech and calculate true GOP."""
    
    def __init__(self):
        self.max_acceptable_distance = 150.0

    def calculate_gop_score(self, child_mfcc: np.ndarray, template_mfcc: np.ndarray) -> dict:
        """
        Calculates Goodness of Pronunciation (GOP) using DTW cost mapping.
        """
        if not DTW_AVAILABLE:
            return {"gop_score": 0.0, "dtw_distance": 0.0, "error": "Dependencies missing"}

        try:
            # Reshape 1D MFCC arrays to 2D for fastdtw compatibility
            child_features = child_mfcc.reshape(-1, 1)
            ref_features = template_mfcc.reshape(-1, 1)
            
            # Calculate temporal alignment distance
            distance, path = fastdtw(child_features, ref_features, dist=euclidean)
            
            # Convert distance to a log-likelihood percentage (0-100)
            # Lower distance = Higher GOP confidence
            gop_raw = max(0, 100 * (1 - (distance / self.max_acceptable_distance)))
            gop_score = round(min(100, gop_raw * 1.2), 2)
            
            return {
                "gop_score": gop_score,
                "dtw_distance": float(distance),
                "path_length": len(path),
                "status": "success"
            }
            
        except Exception as e:
            print(f"Error in DTW alignment: {e}")
            return {"gop_score": 0.0, "dtw_distance": 0.0, "status": "error"}

# Global instance
syllable_aligner = SyllableAligner()
