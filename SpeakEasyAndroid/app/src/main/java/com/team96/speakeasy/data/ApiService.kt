package com.team96.speakeasy.data

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface ApiService {

    @POST("api/auth/register")
    suspend fun register(@Body body: RegisterRequest): AuthResponse

    @POST("api/auth/login")
    suspend fun login(@Body body: LoginRequest): AuthResponse

    @GET("api/auth/me")
    suspend fun me(): User

    @GET("api/therapy/lessons")
    suspend fun lessons(): List<Lesson>

    @GET("api/progress/summary/{userId}")
    suspend fun progressSummary(@Path("userId") userId: String): ProgressSummary
}
