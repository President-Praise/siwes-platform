"""Paystack integration. Each school may have its own keys; otherwise falls back to env."""

import hashlib
import hmac
import os
import secrets

import httpx

PAYSTACK_API = "https://api.paystack.co"


def env_secret_key() -> str:
    return os.environ.get("PAYSTACK_SECRET_KEY", "").strip()


def env_public_key() -> str:
    return os.environ.get("PAYSTACK_PUBLIC_KEY", "").strip()


def school_secret_key(school: dict) -> str:
    return (school.get("paystack_secret_key") or env_secret_key()).strip()


def school_public_key(school: dict) -> str:
    return (school.get("paystack_public_key") or env_public_key()).strip()


def is_configured(school: dict) -> bool:
    return bool(school_secret_key(school))


def new_reference() -> str:
    return "siwes_" + secrets.token_urlsafe(12)


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature:
        return False
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(mac, signature)


async def initialize_transaction(
    *,
    secret: str,
    email: str,
    amount_kobo: int,
    reference: str,
    callback_url: str,
    metadata: dict | None = None,
) -> dict:
    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
    payload = {
        "email": email,
        "amount": amount_kobo,
        "reference": reference,
        "callback_url": callback_url,
    }
    if metadata:
        payload["metadata"] = metadata
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(f"{PAYSTACK_API}/transaction/initialize", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()
