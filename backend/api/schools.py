"""School CRUD and config helpers."""

import json
from datetime import datetime, timezone
from typing import Optional

from .db import get_conn


DEFAULT_CONFIG_KEYS = {
    "degrees": "[]",                # JSON: [{"label": "B.Eng. Mechatronics", "short": "B.Eng."}]
    "departments": "[]",            # JSON: ["Mechanical Engineering", ...]
    "colleges": "[]",               # JSON: ["College of Engineering", ...]
    "submission_clause": "SUBMITTED TO THE {department}, {college}, {university_full_name}",
    "award_clause": "IN PARTIAL FULFILMENT OF THE REQUIREMENT FOR AWARD OF {degree}",
    "report_chapters": "4",
    "siwes_format": "itf_standard",
    "pickup_location": "",
    "business_name": "",
}

DEFAULT_PRICES = {
    "basic": (5000, 0),
    "standard": (8000, 0),
    "premium": (12000, 0),
    "express_addon": (6000, 0),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_school(
    slug: str,
    name: str,
    full_name: str,
    referral_prefix: str,
    *,
    logo_path: Optional[str] = None,
    paystack_secret_key: Optional[str] = None,
    paystack_public_key: Optional[str] = None,
    platform_cut_pct: int = 20,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO schools(created_at, slug, name, full_name, logo_path, referral_prefix, "
            "paystack_secret_key, paystack_public_key, platform_cut_pct, active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (_now(), slug, name, full_name, logo_path, referral_prefix.upper(),
             paystack_secret_key, paystack_public_key, platform_cut_pct),
        )
        school_id = cur.lastrowid
        for k, v in DEFAULT_CONFIG_KEYS.items():
            conn.execute(
                "INSERT OR IGNORE INTO school_config(school_id, key, value) VALUES (?, ?, ?)",
                (school_id, k, v),
            )
        for pkg, (amt, addon) in DEFAULT_PRICES.items():
            conn.execute(
                "INSERT OR IGNORE INTO school_prices(school_id, package, amount, express_addon) VALUES (?, ?, ?, ?)",
                (school_id, pkg, amt, addon),
            )
        return school_id


def get_school(school_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM schools WHERE id = ?", (school_id,)).fetchone()
        return dict(row) if row else None


def get_school_by_slug(slug: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM schools WHERE slug = ? AND active = 1", (slug,)).fetchone()
        return dict(row) if row else None


def list_schools(*, include_inactive: bool = False) -> list[dict]:
    with get_conn() as conn:
        if include_inactive:
            rows = conn.execute("SELECT * FROM schools ORDER BY id ASC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM schools WHERE active = 1 ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]


def update_school(school_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [school_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE schools SET {cols} WHERE id = ?", values)


def get_school_config(school_id: int) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT key, value FROM school_config WHERE school_id = ?",
            (school_id,),
        ).fetchall()
        out = dict(DEFAULT_CONFIG_KEYS)
        for r in rows:
            out[r["key"]] = r["value"]
        return out


def set_school_config(school_id: int, key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO school_config(school_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(school_id, key) DO UPDATE SET value = excluded.value",
            (school_id, key, value),
        )


def update_school_config_bulk(school_id: int, updates: dict[str, str]) -> None:
    with get_conn() as conn:
        for k, v in updates.items():
            conn.execute(
                "INSERT INTO school_config(school_id, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(school_id, key) DO UPDATE SET value = excluded.value",
                (school_id, k, v),
            )


def get_school_prices(school_id: int) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT package, amount, express_addon FROM school_prices WHERE school_id = ?",
            (school_id,),
        ).fetchall()
        out: dict = {}
        for r in rows:
            out[r["package"]] = {"amount": r["amount"], "express_addon": r["express_addon"]}
        for pkg, (amt, addon) in DEFAULT_PRICES.items():
            out.setdefault(pkg, {"amount": amt, "express_addon": addon})
        return out


def update_school_prices(school_id: int, prices: dict[str, dict]) -> None:
    with get_conn() as conn:
        for pkg, data in prices.items():
            amount = int(data.get("amount", 0))
            addon = int(data.get("express_addon", 0))
            conn.execute(
                "INSERT INTO school_prices(school_id, package, amount, express_addon) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(school_id, package) DO UPDATE SET amount = excluded.amount, express_addon = excluded.express_addon",
                (school_id, pkg, amount, addon),
            )


def school_for_payload(school_id: int) -> dict:
    """Returns a school_config dict for report_generator/ppt_generator."""
    school = get_school(school_id) or {}
    cfg = get_school_config(school_id)
    return {
        "name": school.get("name", ""),
        "full_name": school.get("full_name", ""),
        "logo_path": school.get("logo_path"),
        "submission_clause": cfg.get("submission_clause"),
        "award_clause": cfg.get("award_clause"),
    }


# ---- School admins ----

def list_school_admins(school_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, created_at, school_id, username, display_name, active FROM school_admins WHERE school_id = ? ORDER BY id ASC",
            (school_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_school_admin(school_id: int, username: str, pin_hash: str, display_name: str | None = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO school_admins(created_at, school_id, username, pin_hash, display_name, active) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (_now(), school_id, username, pin_hash, display_name),
        )
        return cur.lastrowid


def update_school_admin(admin_id: int, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [admin_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE school_admins SET {cols} WHERE id = ?", values)


def get_school_admin(admin_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM school_admins WHERE id = ?", (admin_id,)).fetchone()
        return dict(row) if row else None
