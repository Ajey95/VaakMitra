package com.team96.speakeasy.data

import java.net.URI

object BackendUrl {
    fun validate(url: String, release: Boolean): String {
        val normalized = if (url.endsWith('/')) url else "$url/"
        val scheme = URI(normalized).scheme?.lowercase()
        require(scheme == "https" || (!release && scheme == "http")) {
            "Backend URL must use HTTPS in release builds"
        }
        require(URI(normalized).host != null) { "Backend URL must include a host" }
        return normalized
    }
}
