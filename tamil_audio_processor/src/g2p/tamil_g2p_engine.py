import json
import os
import logging

logger = logging.getLogger("TamilG2P")

class TamilG2PEngine:
    def __init__(self, dict_path="C:/FinalYear2/tamil_audio_processor/src/g2p/pronunciation_dictionary.json"):
        self.dict_path = dict_path
        self.dictionary = {}
        self.version = "unknown"
        self._load_dictionary()
        
    def _load_dictionary(self):
        if not os.path.exists(self.dict_path):
            logger.error(f"Pronunciation dictionary not found at {self.dict_path}")
            raise FileNotFoundError(f"Pronunciation dictionary not found at {self.dict_path}")
            
        with open(self.dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.dictionary = data.get("words", {})
            self.version = data.get("version", "unknown")
            logger.info(f"Loaded Tamil G2P Dictionary version {self.version} with {len(self.dictionary)} words.")
            
    def get_expected_pronunciation(self, target_word: str) -> dict:
        """
        Looks up the target word in the static dictionary.
        Returns the expected phonemes and syllables.
        """
        word_data = self.dictionary.get(target_word)
        if not word_data:
            logger.warning(f"Word '{target_word}' not found in the dictionary.")
            raise ValueError(f"Word '{target_word}' not found in the pronunciation dictionary.")
            
        return {
            "expected_word": target_word,
            "expected_phonemes": word_data["phonemes"],
            "expected_syllables": word_data["syllables"],
            "dict_version": self.version
        }
