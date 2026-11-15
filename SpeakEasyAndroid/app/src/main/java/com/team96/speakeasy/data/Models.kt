package com.team96.speakeasy.data

import com.squareup.moshi.Json

data class RegisterRequest(
    val email: String,
    val password: String,
    @Json(name = "confirm_password") val confirmPassword: String,
    @Json(name = "full_name") val fullName: String,
    @Json(name = "child_name") val childName: String,
    @Json(name = "child_age") val childAge: Int,
    val language: String = "Tamil",
)

data class LoginRequest(
    val email: String,
    val password: String,
)

data class User(
    val email: String? = null,
    @Json(name = "full_name") val fullName: String? = null,
    @Json(name = "child_name") val childName: String? = null,
    @Json(name = "child_age") val childAge: Int? = null,
    val role: String? = null,
    @Json(name = "total_sessions") val totalSessions: Int? = 0,
    @Json(name = "total_stars") val totalStars: Int? = 0,
    val language: String? = null,
)

data class AuthResponse(
    val message: String? = null,
    @Json(name = "access_token") val accessToken: String,
    @Json(name = "token_type") val tokenType: String? = null,
    val user: User? = null,
)

data class Lesson(
    val id: Int,
    val type: String,
    val symbol: String,
    val english: String,
    val phoneme: String,
    val tip: String,
    val difficulty: Int,
    val airflow: String? = null,
    @Json(name = "candleBlows") val candleBlows: Boolean? = false,
    @Json(name = "avatar_coach") val avatarCoach: AvatarCoach? = null,
)

data class AvatarCoach(
    val enabled: Boolean = false,
    val engine: String? = null,
    val renderer: String? = null,
    val name: String? = null,
    val voice: String? = null,
    @Json(name = "package_path") val packagePath: String? = null,
    val intro: String? = null,
    val tip: String? = null,
    val success: String? = null,
    val retry: String? = null,
)

data class SpeechResult(
    val accuracy: Double? = 0.0,
    @Json(name = "phoneme_match") val phonemeMatch: Boolean? = false,
    @Json(name = "mfcc_score") val mfccScore: Double? = 0.0,
    @Json(name = "gop_score") val gopScore: Double? = 0.0,
    @Json(name = "syllable_scores") val syllableScores: List<SyllableScore>? = emptyList(),
    @Json(name = "weakest_syllable") val weakestSyllable: String? = null,
    val transcription: String? = "",
    val feedback: String? = "",
    val error: String? = null,
)

data class SyllableScore(
    val syllable: String,
    val gop: Double = 0.0,
)

data class SaveProgressRequest(
    @Json(name = "lesson_id") val lessonId: Int,
    val phoneme: String,
    @Json(name = "lesson_type") val lessonType: String,
    val accuracy: Double,
    @Json(name = "phoneme_match") val phonemeMatch: Boolean,
    @Json(name = "mfcc_score") val mfccScore: Double,
    val feedback: String,
    @Json(name = "duration_ms") val durationMs: Long,
)

data class SaveProgressResponse(
    val message: String? = null,
    @Json(name = "stars_earned") val starsEarned: Int? = 0,
    val accuracy: Double? = 0.0,
)

data class ChartPoint(
    val date: String? = null,
    val accuracy: Double? = 0.0,
    @Json(name = "lesson_id") val lessonId: Int? = null,
)

data class ProgressSummary(
    @Json(name = "total_sessions") val totalSessions: Int? = 0,
    @Json(name = "total_stars") val totalStars: Int? = 0,
    @Json(name = "completed_lessons") val completedLessons: Int? = 0,
    @Json(name = "total_lessons") val totalLessons: Int? = 6,
    @Json(name = "avg_accuracy") val avgAccuracy: Double? = 0.0,
    @Json(name = "chart_data") val chartData: List<ChartPoint>? = emptyList(),
)
