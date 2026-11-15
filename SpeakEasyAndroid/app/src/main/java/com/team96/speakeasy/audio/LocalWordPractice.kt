package com.team96.speakeasy.audio

import kotlin.math.abs

/** DEC-013/FUS-007: local capture screening must not invent a word score. */
data class LocalWordOutcome(
    val decision: String = "UNSCORABLE",
    val reason: String,
    val wordMatchProbability: Double? = null,
    val developmentResult: String? = null,
    val targetProbability: Double? = null,
    val targetMargin: Double? = null,
    val referenceSimilarity: Double? = null,
    val engineeringIndex: Double? = null,
    val predictedPhonemes: List<String>? = null,
    val supportAction: String? = null,
    val soundPracticeEvidence: SoundPracticeEvidence? = null,
    val pauseAlignment: PauseAlignmentResult? = null,
    val coachCue: PracticeCoachCue? = null,
    val coachToolResult: CoachToolResult? = null,
)

data class WordPracticePresentation(
    val title: String,
    val guidance: String,
    val scoreLabel: String? = null,
    val detailCode: String? = null,
    val primaryActionLabel: String = "Try again",
    val tokenSequence: String? = null,
    val canAdvancePractice: Boolean = false,
)

object LocalWordPractice {
    /** GOV-001/FUS-007: this unvalidated preview is never an enabled release capture path. */
    fun canCapture(isDebugBuild: Boolean): Boolean = isDebugBuild

    fun assess(targetWord: String, samples: ShortArray, sampleRate: Int = 16000): LocalWordOutcome {
        if (targetWord.isBlank()) return LocalWordOutcome(reason = "TARGET_UNAVAILABLE")
        if (sampleRate != 16000) return LocalWordOutcome(reason = "UNSUPPORTED_SAMPLE_RATE")
        if (samples.size < 4800) return LocalWordOutcome(reason = "TOO_SHORT")
        if (samples.size > 128000) return LocalWordOutcome(reason = "TOO_LONG")
        if (samples.all { it == 0.toShort() }) return LocalWordOutcome(reason = "NO_SPEECH")
        val clipped = samples.count { abs(it.toInt()) >= 32734 }
        if (clipped > samples.size / 100) return LocalWordOutcome(reason = "CLIPPED")
        return LocalWordOutcome(reason = "MODEL_UNAVAILABLE")
    }

    /** DEC079/UX014: learner guidance stays neutral; technical evidence is internal. */
    fun present(outcome: LocalWordOutcome): WordPracticePresentation = when (outcome.reason) {
        "NO_SPEECH" -> WordPracticePresentation(
            "I couldn't hear the word",
            "Keep the phone about a hand-span away, wait for Listening, then say the whole word.",
            detailCode = outcome.reason,
        )
        "VAD_NO_SPEECH" -> WordPracticePresentation(
            "I heard audio, but not a clear word",
            "Wait for Listening, then say the whole word in one natural voice near the phone.",
            detailCode = outcome.reason,
        )
        "TOO_SHORT" -> WordPracticePresentation(
            "I need the whole word",
            "Wait for Listening, say the complete word, then tap Stop.",
            detailCode = outcome.reason,
        )
        "CLIPPED" -> WordPracticePresentation(
            "That was too loud",
            "Move the phone a little farther away and say the whole word in a comfortable voice.",
            detailCode = outcome.reason,
        )
        else -> presentDevelopmentOutcome(outcome)
    }

    private fun presentDevelopmentOutcome(outcome: LocalWordOutcome): WordPracticePresentation = when (outcome.developmentResult) {
        "DEV_PHONEMES" -> WordPracticePresentation(
            "Predicted sounds",
            when(outcome.supportAction) {
                "adult_example" -> "Listen to the whole word if you would like help, then practise at your own pace."
                "picture" -> "Look at the picture if it helps, then practise at your own pace."
                "repeat" -> "You can try the whole word again if you want."
                else -> "These sounds are an estimate. Keep practising at your own pace."
            },
            tokenSequence = outcome.predictedPhonemes?.joinToString(" "),
            primaryActionLabel = "Next word",
            canAdvancePractice = true,
        )
        "DEV_MATCH" -> WordPracticePresentation(
            "Nice practice",
            "You can continue, listen again, or take a break.",
            detailCode = outcome.reason,
            primaryActionLabel = "Continue",
            canAdvancePractice = true,
        )
        "DEV_TRY_AGAIN" -> WordPracticePresentation(
            "Let's practise once more",
            "Listen to the example if it helps, then try when you are ready.",
            detailCode = outcome.reason,
        )
        "DEV_UNCERTAIN" -> WordPracticePresentation(
            "I couldn't tell clearly",
            "Move a little closer, wait for the microphone, and say the whole word again.",
            detailCode = outcome.reason,
        )
        "DEV_UNAVAILABLE" -> WordPracticePresentation(
            "Let's try again",
            "We couldn't get sound feedback this time. You can try again or keep practising.",
            detailCode = outcome.reason,
        )
        else -> when (outcome.reason) {
            "MODEL_UNAVAILABLE" -> WordPracticePresentation("Nice practice", "Try the whole word again when you are ready.", detailCode = outcome.reason)
            else -> WordPracticePresentation("Let's try again", "Say the whole word after the microphone starts.", detailCode = outcome.reason)
        }
    }
}
