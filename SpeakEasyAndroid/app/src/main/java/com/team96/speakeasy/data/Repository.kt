package com.team96.speakeasy.data

import com.team96.speakeasy.BuildConfig
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Single source of truth for network access.
 *
 * BASE_URL comes from BuildConfig (see app/build.gradle.kts). It defaults to
 * 10.0.2.2 — the Android emulator's alias for the host machine's localhost
 * (where the FastAPI backend runs on port 8000). To target a physical device,
 * build with -PbackendUrl=http://<your-pc-lan-ip>:8000/ — no source edit needed.
 */
object Api {
    val BASE_URL: String = BackendUrl.validate(BuildConfig.BASE_URL, !BuildConfig.DEBUG)

    private val moshi: Moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    private val authInterceptor = okhttp3.Interceptor { chain ->
        val builder = chain.request().newBuilder()
        if (!SessionManager.isOfflineReview) SessionManager.token?.let { builder.addHeader("Authorization", "Bearer $it") }
        chain.proceed(builder.build())
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .apply {
            if (BuildConfig.DEBUG) {
                addInterceptor(HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BASIC
                })
            }
        }
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .build()

    val service: ApiService = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(client)
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .build()
        .create(ApiService::class.java)
}
