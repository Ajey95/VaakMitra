import numpy as np
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AudioCaptureService")

class AudioCaptureService:
    def __init__(self, sample_rate=16000, max_duration_sec=10.0):
        """
        Initializes the audio capture service.
        :param sample_rate: Target sample rate (16 kHz)
        :param max_duration_sec: Maximum duration of audio to buffer
        """
        self.sample_rate = sample_rate
        self.max_duration_sec = max_duration_sec
        self.max_samples = int(sample_rate * max_duration_sec)
        
        # In-memory buffer strictly to prevent disk IO
        self.buffer = np.zeros(self.max_samples, dtype=np.float32)
        self.current_size = 0
        
        self.is_capturing = False
        self.start_time = None
        self.cancelled = False

    def start_capture(self):
        """Starts a new capture session, clearing the buffer."""
        self.current_size = 0
        self.buffer.fill(0.0)
        self.is_capturing = True
        self.cancelled = False
        self.start_time = time.time()
        logger.info("Started audio capture.")

    def stop_capture(self):
        """Stops the capture session."""
        self.is_capturing = False
        logger.info(f"Stopped audio capture. Buffered {self.current_size} samples.")

    def cancel_capture(self):
        """Cancels the capture and clears the buffer."""
        self.is_capturing = False
        self.cancelled = True
        self.current_size = 0
        self.buffer.fill(0.0)
        logger.info("Cancelled audio capture and cleared buffer.")

    def ingest_audio_chunk(self, pcm_data: np.ndarray, source_sample_rate: int):
        """
        Ingests a chunk of raw PCM data from Unity/Frontend.
        Must be mono. Performs normalization.
        """
        if not self.is_capturing or self.cancelled:
            return

        # Check timeout
        if time.time() - self.start_time > self.max_duration_sec:
            logger.warning("Max capture duration reached.")
            self.stop_capture()
            return

        # Convert to mono if stereo
        if pcm_data.ndim > 1 and pcm_data.shape[1] > 1:
            pcm_data = np.mean(pcm_data, axis=1)
            
        pcm_data = pcm_data.flatten()
        
        # Target constraint: 16 kHz audio expected from Unity. 
        # Advanced resampling requires SciPy/Librosa, omitted for lightweight edge deployment.
        if source_sample_rate != self.sample_rate:
            raise ValueError(f"Expected {self.sample_rate} Hz, got {source_sample_rate} Hz.")
            
        # Convert to float32 in range [-1.0, 1.0] safely
        if np.issubdtype(pcm_data.dtype, np.integer):
            # Assume 16-bit PCM
            pcm_data = pcm_data.astype(np.float32) / 32768.0
        else:
            pcm_data = pcm_data.astype(np.float32)
            
        # Optional: Reject or flag if max_val is dangerously low, but do not blind-scale noise to 1.0
        # The AudioQualityValidator will catch silent audio.
        samples_to_add = len(pcm_data)
        if self.current_size + samples_to_add > self.max_samples:
            samples_to_add = self.max_samples - self.current_size
            
        if samples_to_add > 0:
            self.buffer[self.current_size:self.current_size + samples_to_add] = pcm_data[:samples_to_add]
            self.current_size += samples_to_add
            
        if self.current_size >= self.max_samples:
            self.stop_capture()

    def get_audio(self) -> np.ndarray:
        """Returns the valid buffered audio."""
        if self.cancelled:
            return np.array([], dtype=np.float32)
        return self.buffer[:self.current_size].copy()
