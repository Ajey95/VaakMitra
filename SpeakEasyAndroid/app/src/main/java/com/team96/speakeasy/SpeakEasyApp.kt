package com.team96.speakeasy

import android.app.Application
import com.team96.speakeasy.data.SessionManager

class SpeakEasyApp : Application() {
    override fun onCreate() {
        super.onCreate()
        SessionManager.init(this)
    }
}
