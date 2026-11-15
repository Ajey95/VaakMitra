package com.team96.speakeasy.viewmodel

/** DEC079/UX014: sign-in failures describe the user's choices, never server setup. */
fun friendlySignInError(message:String):String = when {
    message.contains("Unable to resolve host",true) || message.contains("Failed to connect",true) || message.contains("timeout",true) ->
        "Sign-in is unavailable right now. You can still start learning on this device."
    message.contains("400") -> "Email already registered or invalid details."
    message.contains("401") -> "Invalid email or password."
    else -> "Something went wrong. Please try again."
}
