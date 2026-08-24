"""Unified auth for super_admin and school_admin roles. PIN-based + bcrypt + sessions."""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Cookie, Depends, HTTPException, Request, Response

from .db import get_conn

SESSION_COOKIE = "platform_session"
SESSION_TTL_SECONDS = 8 * 60 * 60

RATE_WINDOW_SECONDS = 300
RATE_MAX_ATTEMPTS = 5
RATE_LOCKOUT_SECONDS = 900

_RATE: dict[str, list[datetime]] = {}
_LOCKOUTS: dict[str, datetime] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_pin(pin: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pin.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def rate_limit_check(ip: str) -> None:
    locked_until = _LOCKOUTS.get(ip)
    if locked_until and _now() < locked_until:
        secs = int((locked_until - _now()).total_seconds())
        raise HTTPException(status_code=429, detail=f"Locked out. Try again in {secs}s.")


def rate_limit_record(ip: str) -> None:
    now = _now()
    attempts = [t for t in _RATE.get(ip, []) if (now - t).total_seconds() < RATE_WINDOW_SECONDS]
    attempts.append(now)
    _RATE[ip] = attempts
    if len(attempts) >= RATE_MAX_ATTEMPTS:
        _LOCKOUTS[ip] = now + timedelta(seconds=RATE_LOCKOUT_SECONDS)


def rate_limit_clear(ip: str) -> None:
    _RATE.pop(ip, None)
    _LOCKOUTS.pop(ip, None)


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_session(*, role: str, school_admin_id: Optional[int], school_id: Optional[int], ip: Optional[str]) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    created = _now()
    expires = created + timedelta(seconds=SESSION_TTL_SECONDS)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions(token, created_at, expires_at, ip_address, role, school_admin_id, school_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (token, created.isoformat(), expires.isoformat(), ip, role, school_admin_id, school_id),
        )
    return token, expires


def delete_session(token: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def purge_expired_sessions() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (_now().isoformat(),))


def get_session_row(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
        if not row:
            return None
        try:
            expires = datetime.fromisoformat(row["expires_at"])
        except Exception:
            return None
        if expires < _now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
        return dict(row)


def require_session(
    request: Request,
    platform_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict:
    sess = get_session_row(platform_session)
    if not sess:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sess


def require_super_admin(session: dict = Depends(require_session)) -> dict:
    if session.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin only")
    return session


def require_school_admin(
    request: Request,
    session: dict = Depends(require_session),
) -> dict:
    """Allows either school_admin (their own school) OR super_admin (any school via ?school_id=)."""
    role = session.get("role")
    if role not in ("super_admin", "school_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return session


def resolved_school_id(session: dict, request: Request) -> int:
    """Returns the effective school_id for a school-scoped route.

    For school_admin: their own school_id (query param ignored).
    For super_admin: the ?school_id= query param (required).
    """
    if session.get("role") == "school_admin":
        sid = session.get("school_id")
        if not sid:
            raise HTTPException(status_code=403, detail="School admin missing school_id")
        return int(sid)
    qp = request.query_params.get("school_id")
    if not qp:
        raise HTTPException(status_code=400, detail="?school_id= required for super_admin")
    try:
        return int(qp)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid school_id")


# ---- Super admin bootstrap ----

def super_admin_exists() -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM super_admin LIMIT 1").fetchone()
        return row is not None


def set_super_admin_pin(pin: str) -> None:
    if len(pin) < 4:
        raise ValueError("PIN must be at least 4 characters")
    h = hash_pin(pin)
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM super_admin LIMIT 1").fetchone()
        if existing:
            conn.execute("UPDATE super_admin SET pin_hash = ? WHERE id = ?", (h, existing["id"]))
        else:
            conn.execute("INSERT INTO super_admin(pin_hash) VALUES (?)", (h,))


def verify_super_admin_pin(pin: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT pin_hash FROM super_admin LIMIT 1").fetchone()
        if not row:
            return False
        return verify_pin(pin, row["pin_hash"])


def seed_super_admin_from_env() -> None:
    if super_admin_exists():
        return
    pin = os.environ.get("SUPER_ADMIN_INITIAL_PIN", "").strip()
    if pin:
        set_super_admin_pin(pin)


# ---- School admin auth ----

def verify_school_admin_credentials(username: str, pin: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM school_admins WHERE username = ? AND active = 1",
            (username,),
        ).fetchone()
        if not row:
            return None
        if not verify_pin(pin, row["pin_hash"]):
            return None
        return dict(row)


def set_session_cookie(response: Response, token: str, expires: datetime) -> None:
    secure_cookie = os.environ.get("COOKIE_SECURE", "0") == "1"
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        expires=int((expires - _now()).total_seconds()),
        httponly=True,
        samesite="lax",
        secure=secure_cookie,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")
