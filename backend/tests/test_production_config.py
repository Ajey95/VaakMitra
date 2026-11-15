"""Production configuration contract tests."""
import pytest
from pydantic import ValidationError

from app.config import Settings


def test_cors_and_host_lists_are_normalized():
    config = Settings(
        _env_file=None,
        CORS_ORIGIN="https://app.example.com/",
        CORS_ORIGINS="https://app.example.com, https://preview.example.com",
        TRUSTED_HOSTS="app.example.com, api.example.com",
    )
    assert config.cors_origins == ["https://app.example.com", "https://preview.example.com"]
    assert config.trusted_hosts == ["app.example.com", "api.example.com"]


def test_development_accepts_both_local_browser_origins():
    config = Settings(_env_file=None, APP_ENV="development", CORS_ORIGIN="")

    assert "http://localhost:5173" in config.cors_origins
    assert "http://127.0.0.1:5173" in config.cors_origins


def test_production_rejects_short_or_default_secret():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APP_ENV="production", JWT_SECRET_KEY="too-short")


def test_production_requires_secure_cookies_and_real_admin_password():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            APP_ENV="production",
            JWT_SECRET_KEY="x" * 48,
            ADMIN_PASSWORD="A-secure-password-123",
            COOKIE_SECURE=False,
        )


def test_cloudinary_feature_flag_is_explicit():
    config = Settings(_env_file=None)
    assert config.cloudinary_enabled is False


def test_public_or_adaptive_production_mode_is_rejected():
    common = {
        "_env_file": None,
        "APP_ENV": "production",
        "JWT_SECRET_KEY": "x" * 48,
        "ADMIN_PASSWORD": "A-secure-password-123",
        "COOKIE_SECURE": True,
        "CORS_ORIGIN": "https://vaakmitra.lan",
    }
    with pytest.raises(ValidationError):
        Settings(**common, VAAKMITRA_DEPLOYMENT_MODE="public_cloud")
    with pytest.raises(ValidationError):
        Settings(
            **common,
            VAAKMITRA_DEPLOYMENT_MODE="private_edge",
            VAAKMITRA_POLICY_MODE="active",
        )


def test_private_deterministic_production_mode_is_accepted():
    config = Settings(
        _env_file=None,
        APP_ENV="production",
        JWT_SECRET_KEY="x" * 48,
        ADMIN_PASSWORD="A-secure-password-123",
        COOKIE_SECURE=True,
        CORS_ORIGIN="https://vaakmitra.lan",
        VAAKMITRA_DEPLOYMENT_MODE="private_edge",
        VAAKMITRA_POLICY_MODE="deterministic",
        VAAKMITRA_SYNC_ENABLED=False,
    )

    assert config.VAAKMITRA_DEPLOYMENT_MODE == "private_edge"
