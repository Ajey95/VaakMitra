import unittest
import numpy as np
import time

from src.audio.audio_capture_service import AudioCaptureService
from src.audio.audio_quality_validator import AudioQualityValidator
from src.audio.vad_service import VADService

class TestAudioPipeline(unittest.TestCase):
    def test_audio_capture_and_buffer(self):
        service = AudioCaptureService(sample_rate=16000, max_duration_sec=2.0)
        service.start_capture()
        
        # Simulate feeding 1 second of audio
        dummy_audio = np.ones(16000, dtype=np.float32)
        service.ingest_audio_chunk(dummy_audio, 16000)
        
        audio_out = service.get_audio()
        self.assertEqual(len(audio_out), 16000)
        self.assertTrue(service.is_capturing)
        
        service.stop_capture()
        self.assertFalse(service.is_capturing)
        
    def test_audio_timeout(self):
        service = AudioCaptureService(sample_rate=16000, max_duration_sec=1.0)
        service.start_capture()
        
        service.start_time = time.time() - 2.0 # Force timeout
        dummy_audio = np.ones(16000, dtype=np.float32)
        service.ingest_audio_chunk(dummy_audio, 16000)
        
        self.assertFalse(service.is_capturing) # Should be stopped automatically
        
    def test_quality_validator(self):
        validator = AudioQualityValidator()
        
        # Too short
        res = validator.validate(np.ones(100), 16000)
        self.assertEqual(res["reason"], "too_short")
        
        # Silent
        res = validator.validate(np.zeros(16000), 16000)
        self.assertEqual(res["reason"], "silent")
        
        # Clipped
        res = validator.validate(np.ones(16000), 16000)
        self.assertEqual(res["reason"], "clipped")

if __name__ == '__main__':
    unittest.main()
