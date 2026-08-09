import unittest
import numpy as np

from src.alignment.forced_aligner import CTCForcedAligner
from src.g2p.tamil_g2p_engine import TamilG2PEngine

class TestAlignmentEngine(unittest.TestCase):
    def test_forced_alignment(self):
        g2p = TamilG2PEngine()
        expected = g2p.get_expected_pronunciation("அம்மா")
        expected_phonemes = expected["expected_phonemes"]
        
        # Mocking log probabilities for 50 frames (1 second total)
        # assuming a 40-class phoneme vocabulary. We will just pass the expected phonemes
        # directly in the mock since our aligner doesn't have the vocab mapping
        log_probs = np.random.uniform(-5.0, 0.0, size=(50, 40))
        
        aligner = CTCForcedAligner()
        result = aligner.align(expected_phonemes, log_probs)
        
        self.assertEqual(len(result["phoneme_alignment"]), len(expected_phonemes))
        self.assertTrue(0.0 <= result["alignment_confidence"] <= 1.0)
        self.assertEqual(result["phoneme_alignment"][0]["phoneme"], "a")

if __name__ == '__main__':
    unittest.main()
