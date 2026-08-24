"""Shared config helpers (URL builders, project root)."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def public_base_url(request_base: str | None = None) -> str:
    env_url = os.environ.get("PUBLIC_BASE_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")
    if request_base:
        return request_base.rstrip("/")
    return "http://127.0.0.1:8000"


def callback_url(school_slug: str, order_id: int, request_base: str | None = None) -> str:
    return f"{public_base_url(request_base)}/{school_slug}/orders/{order_id}/status"
