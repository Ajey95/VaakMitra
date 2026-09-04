"""
Centralised, environment-driven configuration for the ASD-Edge-ST backend.

All settings are loaded from environment variables (or a .env file).
No secrets are hard-coded here.
"""

from __future__ import annotations

from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_prefix="ASD_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    db_key: str = Field(
        default="dev_insecure_key_change_me",
        description="SQLCipher encryption key. Must be overridden in production.",
    )
    db_path: Path = Field(
        default=Path("./asd_local.db"),
        description="Path to the encrypted local SQLite database.",
    )

    # ── Therapist sync ────────────────────────────────────────────────────────
    sync_base_url: str = Field(
        default="http://localhost:9000",
        description="Base URL of the remote therapist server.",
    )
    sync_api_token: str = Field(
        default="dev_token",
        description="Bearer token for therapist API authentication.",
    )
    sync_max_retries: int = Field(default=5, ge=0)
    sync_backoff_factor: float = Field(default=2.0, gt=0)
    sync_timeout_s: float = Field(default=10.0, gt=0)

    # ── Local API server ──────────────────────────────────────────────────────
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8765, ge=1024, le=65535)
    max_audio_bytes: int = Field(
        default=320_000,
        gt=0,
        description="Maximum in-memory PCM payload (10 s at 16 kHz mono int16).",
    )
    member1_timeout_s: float = Field(default=15.0, gt=0)
    member2_timeout_s: float = Field(default=20.0, gt=0)
    dictionary_version: str = Field(default="ta-dict-1.0.0", min_length=1)
    model_version: str = Field(default="unconfigured", min_length=1)
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated browser frontend origins; Unity native is unaffected.",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")

    # ── Policy / model versioning ─────────────────────────────────────────────
    policy_path: Path = Field(
        default=Path("./config/default_policy.json"),
        description="Path to the active therapist policy JSON file.",
    )

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got {v!r}")
        return upper


# Singleton — import this everywhere
settings = Settings()
