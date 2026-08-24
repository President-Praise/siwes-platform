"""Platform-level settings (super admin scope)."""

from datetime import datetime, timezone

from .db import get_conn


DEFAULTS = {
    "platform_name": "SIWES Report Platform",
    "default_cut_pct": "20",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM platform_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO platform_settings(key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, _now()),
        )


def seed_defaults() -> None:
    for k, v in DEFAULTS.items():
        if get(k) is None:
            set_(k, v)


def all_settings() -> dict:
    out = dict(DEFAULTS)
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM platform_settings").fetchall()
        for r in rows:
            out[r["key"]] = r["value"]
    return out
