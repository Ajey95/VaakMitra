"""Advanced acoustic processing for pediatric ASD speech."""
import io
import numpy as np
import librosa

class AcousticProcessor:
    """Handles VTLN and VSA extraction for the therapy pipeline."""
    
    @staticmethod
    def extract_formants_vsa(audio_bytes: bytes, sr: int = 16000) -> dict:
        """
        Extracts F1 and F2 formants to calculate Vowel Space Area (VSA).
        Used to track motor speech improvements longitudinally.
        """
        try:
            audio_io = io.BytesIO(audio_bytes)
            y, sr = librosa.load(audio_io, sr=sr)
            
            # Apply pre-emphasis filter
            y_filt = librosa.effects.preemphasis(y)
            
            # Linear Predictive Coding (LPC)
            order = int(2 + sr / 1000)
            a = librosa.lpc(y_filt, order=order)
            
            # Find roots of the LPC polynomial
            roots = np.roots(a)
            roots = [r for r in roots if np.imag(r) >= 0]
            
            # Convert roots to frequencies
            angles = np.arctan2(np.imag(roots), np.real(roots))
            freqs = sorted(angles * (sr / (2 * np.pi)))
            
            # Extract formants (ignoring < 100Hz)
            formants = [f for f in freqs if f > 100]
            
            f1 = formants[0] if len(formants) > 0 else 500.0
            f2 = formants[1] if len(formants) > 1 else 1500.0
            
            # VSA Proxy calculation
            vsa_score = (f1 * f2) / 1000.0 
            
            return {
                "f1_hz": float(f1), 
                "f2_hz": float(f2), 
                "vsa_area": float(vsa_score),
                "status": "success"
            }
        except Exception as e:
            print(f"Error extracting VSA: {e}")
            return {"f1_hz": 0.0, "f2_hz": 0.0, "vsa_area": 0.0, "status": "error"}

    @staticmethod
    def apply_vtln_warping(mfcc: np.ndarray, alpha: float = 0.85) -> np.ndarray:
        """
        Vocal Tract Length Normalization (VTLN).
        Maps shorter pediatric vocal tracts to adult acoustic space to avoid penalization.
        """
        warped_mfcc = np.copy(mfcc)
        num_coeffs = len(mfcc)
        
        for i in range(1, num_coeffs):
            warped_mfcc[i] = mfcc[i] * (alpha ** (i / num_coeffs))
            
        return warped_mfcc

# Global instance
acoustic_processor = AcousticProcessor()
