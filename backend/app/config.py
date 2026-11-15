"""Application configuration.

The API is deployed in two different environments (local development and
Render).  Keeping the validation here means a misconfigured production
service fails at boot instead of silently running with insecure defaults.
"""
from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    APP_ENV: str = "development"
    MONGODB_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "speakeasy_asd"
    JWT_SECRET_KEY: str = "development-only-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ACCESS_COOKIE_NAME: str = "speakeasy_access"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "change-this-password"
    CORS_ORIGIN: str = ""
    CORS_ORIGINS: str = ""
    TRUSTED_HOSTS: str = "localhost,127.0.0.1"
    MAX_UPLOAD_BYTES: int = 8 * 1024 * 1024
    EXPOSE_DEV_CODES: bool = False
    MONGODB_TLS_ALLOW_INVALID_CERTIFICATES: bool = False
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_STORY_VOICE_ID: str = ""
    VAAKMITRA_BUNDLE_CONFIG: str = ""
    VAAKMITRA_DEPLOYMENT_MODE: str = "development"
    VAAKMITRA_INFERENCE_TIMEOUT_SECONDS: int = 8
    VAAKMITRA_POLICY_MODE: str = "deterministic"
    VAAKMITRA_SYNC_ENABLED: bool = False
    VAAKMITRA_ALLOWED_THERAPIST_SERVICE_HOSTS: str = ""
    VAAKMITRA_LOG_LEVEL: str = "INFO"
    VAAKMITRA_DIAGNOSTICS_ENABLED: bool = False
    VAAKMITRA_DIAGNOSTIC_CONFIG: str = ""
    DATABASE_TIMEOUT_SECONDS: float = 3.0

    @field_validator("APP_ENV", mode="before")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return str(value).strip().lower()

    @field_validator("COOKIE_SAMESITE")
    @classmethod
    def validate_samesite(cls, value: str) -> str:
        value = value.lower()
        if value not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        return value

    @field_validator("VAAKMITRA_DEPLOYMENT_MODE", "VAAKMITRA_POLICY_MODE", "VAAKMITRA_LOG_LEVEL", mode="before")
    @classmethod
    def normalize_vaakmitra_values(cls, value: str) -> str:
        return str(value).strip().lower()

    @model_validator(mode="after")
    def validate_production_values(self):
        if self.APP_ENV in {"production", "prod"}:
            if self.VAAKMITRA_DIAGNOSTICS_ENABLED:
                raise ValueError("diagnostics are development-only")
            if len(self.JWT_SECRET_KEY) < 32 or self.JWT_SECRET_KEY in {"development-only-change-me", "replace-with-a-long-random-secret"}:
                raise ValueError("JWT_SECRET_KEY must be at least 32 random characters in production")
            if self.ADMIN_PASSWORD in {"change-this-password", "replace-with-a-strong-password"} or len(self.ADMIN_PASSWORD) < 12:
                raise ValueError("ADMIN_PASSWORD must be at least 12 characters in production")
            if not self.COOKIE_SECURE:
                raise ValueError("COOKIE_SECURE must be true in production")
            if not self.CORS_ORIGINS and not self.CORS_ORIGIN:
                raise ValueError("At least one CORS origin is required in production")
            if self.VAAKMITRA_DEPLOYMENT_MODE != "private_edge":
                raise ValueError("VAAKMITRA_DEPLOYMENT_MODE must be private_edge in production")
            if self.VAAKMITRA_SYNC_ENABLED:
                raise ValueError("VAAKMITRA_SYNC_ENABLED must be false in production V1")
            if self.VAAKMITRA_POLICY_MODE != "deterministic":
                raise ValueError("VAAKMITRA_POLICY_MODE must be deterministic in production V1")
        return self

    @property
    def cors_origins(self) -> List[str]:
        """Return de-duplicated origins from legacy and multi-origin settings."""
        values = [self.CORS_ORIGIN, *(self.CORS_ORIGINS.split(",") if self.CORS_ORIGINS else [])]
        origins = list(dict.fromkeys(origin.strip().rstrip("/") for origin in values if origin.strip()))
        local_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
        if self.APP_ENV == "development" and (
            not origins or any(origin in local_origins for origin in origins)
        ):
            origins = list(dict.fromkeys([*origins, *local_origins]))
        return origins

    @property
    def trusted_hosts(self) -> List[str]:
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()]

    @property
    def cloudinary_enabled(self) -> bool:
        return all((self.CLOUDINARY_CLOUD_NAME, self.CLOUDINARY_API_KEY, self.CLOUDINARY_API_SECRET))


settings = Settings()
