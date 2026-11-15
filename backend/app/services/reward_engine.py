"""Reward calculation engine."""
from typing import Dict


class RewardEngine:
    """Calculate rewards and stars for therapy sessions."""
    
    @staticmethod
    def calculate_stars(accuracy: float) -> int:
        """
        Calculate stars earned based on accuracy.
        
        Args:
            accuracy: Accuracy score (0-100)
            
        Returns:
            Number of stars (0-3)
        """
        if accuracy >= 90:
            return 3
        elif accuracy >= 70:
            return 2
        elif accuracy >= 50:
            return 1
        else:
            return 0
    
    @staticmethod
    def get_motivational_message(stars: int, accuracy: float) -> str:
        """Get motivational message based on performance."""
        messages = {
            3: [
                "🌟 Outstanding! You're a superstar!",
                "🎉 Perfect! You're amazing!",
                "⭐ Incredible work! Keep it up!",
                "🏆 You're a champion!",
                "✨ Brilliant! You did it perfectly!",
                "🎯 Wow! That was perfect!",
                "💫 Excellent! You're on fire!",
                "🌈 Fantastic! You're doing great!"
            ],
            2: [
                "⭐ Great job! You're doing really well!",
                "👏 Well done! Almost perfect!",
                "💪 Awesome! Keep practicing!",
                "🎵 Very good! You're improving!",
                "🌟 Nice work! Try once more!",
                "✨ Good effort! You're getting better!"
            ],
            1: [
                "👍 Good try! Practice makes perfect!",
                "💡 Nice start! Let's try again!",
                "🌱 Good effort! Keep going!",
                "🎈 You're learning! Try once more!",
                "🌟 Keep trying! You can do it!"
            ],
            0: [
                "💪 Let's try again together!",
                "🎯 Don't give up! You can do it!",
                "🌈 Keep practicing! You'll get it!",
                "✨ Listen carefully and try again!",
                "💫 You're learning! Let's practice more!"
            ]
        }
        
        import random
        return random.choice(messages.get(stars, messages[0]))
    
    @staticmethod
    def should_unlock_next_lesson(
        current_lesson_id: int,
        best_accuracy: float
    ) -> bool:
        """
        Determine if next lesson should be unlocked.
        
        Args:
            current_lesson_id: Current lesson ID
            best_accuracy: Best accuracy achieved for current lesson
            
        Returns:
            True if next lesson should be unlocked
        """
        # Unlock next lesson if achieved at least 1 star (50% accuracy)
        return best_accuracy >= 50.0
    
    @staticmethod
    def calculate_session_bonus(
        consecutive_success: int,
        session_duration_ms: int
    ) -> Dict:
        """
        Calculate bonus rewards for session metrics.
        
        Args:
            consecutive_success: Number of consecutive successful attempts
            session_duration_ms: Session duration in milliseconds
            
        Returns:
            Dictionary with bonus details
        """
        bonus_stars = 0
        bonus_message = ""
        
        # Streak bonus
        if consecutive_success >= 5:
            bonus_stars += 2
            bonus_message = "🔥 Amazing streak! +2 bonus stars!"
        elif consecutive_success >= 3:
            bonus_stars += 1
            bonus_message = "🔥 Great streak! +1 bonus star!"
        
        # Quick completion bonus (under 2 minutes)
        if session_duration_ms < 120000 and session_duration_ms > 10000:
            bonus_stars += 1
            if bonus_message:
                bonus_message += " Quick learner! +1 star!"
            else:
                bonus_message = "⚡ Quick learner! +1 bonus star!"
        
        return {
            "bonus_stars": bonus_stars,
            "bonus_message": bonus_message
        }


# Global instance
reward_engine = RewardEngine()
