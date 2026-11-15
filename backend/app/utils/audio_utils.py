"""Audio processing utilities."""
import numpy as np
import io

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[WARNING] librosa not installed. Speech scoring will use fallback mode.")

try:
    from scipy.io import wavfile
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def extract_mfcc(audio_bytes: bytes, sr: int = 16000, n_mfcc: int = 13) -> np.ndarray:
    """Extract MFCC features from audio."""
    if not LIBROSA_AVAILABLE:
        return np.zeros(n_mfcc)
    try:
        audio_io = io.BytesIO(audio_bytes)
        y, sr = librosa.load(audio_io, sr=sr)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
        mfcc_mean = np.mean(mfcc, axis=1)
        return mfcc_mean
    except Exception as e:
        print(f"Error extracting MFCC: {e}")
        return np.zeros(n_mfcc)


def calculate_airflow_score(audio_bytes: bytes, sr: int = 16000) -> float:
    """Calculate airflow score from audio energy and zero-crossing rate."""
    if not LIBROSA_AVAILABLE:
        return 0.5
    try:
        audio_io = io.BytesIO(audio_bytes)
        y, sr = librosa.load(audio_io, sr=sr)
        energy = np.sum(y ** 2) / len(y)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        zcr_mean = np.mean(zcr)
        airflow_score = min(1.0, (energy * 1000 + zcr_mean) / 2)
        return float(airflow_score)
    except Exception as e:
        print(f"Error calculating airflow: {e}")
        return 0.5


def calculate_audio_similarity(mfcc1: np.ndarray, mfcc2: np.ndarray) -> float:
    """
    Calculate similarity between two MFCC vectors.
    Returns score from 0-100.
    """
    try:
        mfcc1_norm = mfcc1 / (np.linalg.norm(mfcc1) + 1e-8)
        mfcc2_norm = mfcc2 / (np.linalg.norm(mfcc2) + 1e-8)
        cosine_sim = np.dot(mfcc1_norm, mfcc2_norm)
        euclidean_dist = np.linalg.norm(mfcc1_norm - mfcc2_norm)
        euclidean_sim = 1 / (1 + euclidean_dist)
        combined_sim = (cosine_sim * 0.7 + euclidean_sim * 0.3)
        if combined_sim >= 0:
            score = 65 + (combined_sim * 35)
        else:
            score = 65 + (combined_sim * 35)
        if score >= 50:
            score = 50 + ((score - 50) * 1.3)
        score = max(0, min(100, score))
        return float(score)
    except Exception as e:
        print(f"Error calculating similarity: {e}")
        return 60.0
