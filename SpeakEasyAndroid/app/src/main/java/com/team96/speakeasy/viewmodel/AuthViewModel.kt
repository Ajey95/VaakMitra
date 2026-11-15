package com.team96.speakeasy.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.team96.speakeasy.data.Api
import com.team96.speakeasy.data.LoginRequest
import com.team96.speakeasy.data.RegisterRequest
import com.team96.speakeasy.data.SessionManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class AuthUiState(
    val loading: Boolean = false,
    val error: String? = null,
    val loggedIn: Boolean = SessionManager.isLoggedIn,
)

class AuthViewModel(private val preview:Boolean=false) : ViewModel() {

    private val _state = MutableStateFlow(if(preview)AuthUiState(loggedIn=false) else AuthUiState())
    val state: StateFlow<AuthUiState> = _state

    fun login(email: String, password: String) {
        if(preview)return
        if (email.isBlank() || password.isBlank()) {
            _state.value = _state.value.copy(error = "Please fill in both fields")
            return
        }
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val res = Api.service.login(LoginRequest(email.trim(), password))
                SessionManager.save(res.accessToken, res.user)
                _state.value = AuthUiState(loggedIn = true)
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false, error = friendly(e))
            }
        }
    }

    fun register(
        email: String,
        password: String,
        confirm: String,
        fullName: String,
        childName: String,
        childAge: Int,
        language: String,
    ) {
        if(preview)return
        when {
            listOf(email, password, fullName, childName).any { it.isBlank() } ->
                _state.value = _state.value.copy(error = "Please fill in all fields")
            password.length < 8 ->
                _state.value = _state.value.copy(error = "Password must be at least 8 characters")
            password != confirm ->
                _state.value = _state.value.copy(error = "Passwords do not match")
            childAge !in 7..14 ->
                _state.value = _state.value.copy(error = "Child age must be between 7 and 14")
            else -> {
                _state.value = _state.value.copy(loading = true, error = null)
                viewModelScope.launch {
                    try {
                        val res = Api.service.register(
                            RegisterRequest(
                                email = email.trim(),
                                password = password,
                                confirmPassword = confirm,
                                fullName = fullName.trim(),
                                childName = childName.trim(),
                                childAge = childAge,
                                language = language,
                            )
                        )
                        SessionManager.save(res.accessToken, res.user)
                        _state.value = AuthUiState(loggedIn = true)
                    } catch (e: Exception) {
                        _state.value = _state.value.copy(loading = false, error = friendly(e))
                    }
                }
            }
        }
    }

    fun clearError() {
        _state.value = _state.value.copy(error = null)
    }

    fun startOfflineReview() {
        if(preview || _state.value.loading)return
        _state.value = _state.value.copy(loading=true,error=null)
        viewModelScope.launch {
            try {
                SessionManager.startOfflineReview()
                _state.value = AuthUiState(loggedIn = true)
            } catch(cancelled:kotlinx.coroutines.CancellationException) { throw cancelled
            } catch(_:Exception) {
                _state.value = AuthUiState(error="Couldn't open your local profile. Please try again.",loggedIn=false)
            }
        }
    }

    fun logout(onDone: () -> Unit) {
        if(preview)return
        viewModelScope.launch {
            try {
                Api.service // best effort; backend logout clears cookie only
            } catch (_: Exception) {
            }
            SessionManager.clear()
            _state.value = AuthUiState(loggedIn = false)
            onDone()
        }
    }

    private fun friendly(e: Exception): String {
        return friendlySignInError(e.message.orEmpty())
    }
}
