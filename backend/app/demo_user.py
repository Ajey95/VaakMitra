"""Development-only demo identity for running the product without MongoDB."""
from hmac import compare_digest

from .config import settings


DEMO_USER = {
    "_id": "000000000000000000000001",
    "email": "demo@speakeasy.app",
    "full_name": "Demo Parent",
    "child_name": "Kavi",
    "child_age": 7,
    "language": "Tamil",
    "role": "user",
    "total_sessions": 12,
    "total_stars": 180,
    "is_demo": True,
}


def demo_login_enabled() -> bool:
    """Keep the bundled identity strictly outside production."""
    return settings.APP_ENV not in {"production", "prod"}


def is_demo_credentials(email: str, password: str) -> bool:
    """Authenticate the documented demo credentials without a database."""
    return (
        demo_login_enabled()
        and compare_digest(email.lower(), DEMO_USER["email"])
        and compare_digest(password, "Demo@1234")
    )


def is_demo_email(email: str) -> bool:
    return demo_login_enabled() and compare_digest(email.lower(), DEMO_USER["email"])


def public_demo_user() -> dict:
    return {key: value for key, value in DEMO_USER.items() if key != "_id"}
