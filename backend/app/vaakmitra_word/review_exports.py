"""GOV-003/004/006: authenticated review metadata export integrity."""

from __future__ import annotations

import hashlib
import hmac
import json


def _canonical(payload: dict) -> bytes:
    body = {key: value for key, value in payload.items() if key != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def clinical_bundle_hash(sections: dict[str, str]) -> str:
    """GOV-005: one digest binds all ten reviewed content sections."""
    return hashlib.sha256(_canonical(sections)).hexdigest()


def sign_review_export(payload: dict, key: str) -> dict:
    if len(key.encode("utf-8")) < 32:
        raise ValueError("review_signing_key_too_short")
    digest = hmac.new(key.encode("utf-8"), _canonical(payload), hashlib.sha256).hexdigest()
    return {**payload, "signature": f"hmac-sha256:{digest}"}


def verify_review_export(payload: dict, key: str) -> bool:
    if len(key.encode("utf-8")) < 32:
        return False
    signature = payload.get("signature")
    if not isinstance(signature, str):
        return False
    expected = sign_review_export(payload, key)["signature"]
    return hmac.compare_digest(signature, expected)
