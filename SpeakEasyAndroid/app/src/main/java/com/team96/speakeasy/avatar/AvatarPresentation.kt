package com.team96.speakeasy.avatar

enum class AvatarPhase { IDLE, PROMPTING, LISTENING, PROCESSING, PRAISE, COACH, RETRY, BREAK, ERROR }
enum class AvatarExpression { WARM, SPEAKING, ATTENTIVE, THINKING, JOY, ENCOURAGING, REASSURING, CALM, CONCERNED }
enum class AvatarGesture { REST, EXPLAIN, LISTEN, SETTLE, CELEBRATE, DEMONSTRATE, INVITE, STILL }
enum class AvatarMouth { NEUTRAL, M, A, E, O }

data class AvatarPresentation(val expression: AvatarExpression, val gesture: AvatarGesture) {
    companion object {
        /** DEC-026/AVT-004: UI state maps to presentation; it never changes therapy policy. */
        fun forPhase(phase: AvatarPhase, motion: AvatarMotion = AvatarMotion.GENTLE): AvatarPresentation {
            val presentation = when (phase) {
                AvatarPhase.IDLE -> AvatarPresentation(AvatarExpression.WARM, AvatarGesture.REST)
                AvatarPhase.PROMPTING -> AvatarPresentation(AvatarExpression.SPEAKING, AvatarGesture.EXPLAIN)
                AvatarPhase.LISTENING -> AvatarPresentation(AvatarExpression.ATTENTIVE, AvatarGesture.LISTEN)
                AvatarPhase.PROCESSING -> AvatarPresentation(AvatarExpression.THINKING, AvatarGesture.SETTLE)
                AvatarPhase.PRAISE -> AvatarPresentation(AvatarExpression.JOY, AvatarGesture.CELEBRATE)
                AvatarPhase.COACH -> AvatarPresentation(AvatarExpression.ENCOURAGING, AvatarGesture.DEMONSTRATE)
                AvatarPhase.RETRY -> AvatarPresentation(AvatarExpression.REASSURING, AvatarGesture.INVITE)
                AvatarPhase.BREAK -> AvatarPresentation(AvatarExpression.CALM, AvatarGesture.REST)
                AvatarPhase.ERROR -> AvatarPresentation(AvatarExpression.CONCERNED, AvatarGesture.STILL)
            }
            return if (motion == AvatarMotion.STILL) presentation.copy(gesture = AvatarGesture.STILL) else presentation
        }

        fun mouth(speaking: Boolean, audioLevel: Float): AvatarMouth {
            if (!speaking) return AvatarMouth.NEUTRAL
            return when (audioLevel.coerceIn(0f, 1f)) {
                in .75f..1f -> AvatarMouth.A
                in .5f..<.75f -> AvatarMouth.O
                in .25f..<.5f -> AvatarMouth.E
                else -> AvatarMouth.M
            }
        }
    }
}
