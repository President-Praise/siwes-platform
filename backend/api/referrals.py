"""School-scoped referral system. Codes are unique platform-wide (single referral_code index).

Credits are scoped to (school_id, matric_no).
"""

import secrets
import string
from datetime import datetime, timezone
from typing import Optional

from .db import get_conn

DISCOUNT_NGN = 1500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_code(prefix: str) -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(5))
    return f"{prefix}-{suffix}"


def assign_code_if_missing(order_id: int, prefix: str) -> Optional[str]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT referral_code, status FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if not row or row["referral_code"]:
            return row["referral_code"] if row else None
        for _ in range(8):
            code = _generate_code(prefix)
            try:
                cur = conn.execute(
                    "UPDATE orders SET referral_code = ? WHERE id = ? AND referral_code IS NULL",
                    (code, order_id),
                )
                if cur.rowcount > 0:
                    return code
            except Exception:
                continue
        return None


def find_owner_matric_and_school(code: str) -> Optional[tuple[str, int]]:
    if not code:
        return None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT matric_no, school_id FROM orders WHERE referral_code = ? LIMIT 1",
            (code.strip().upper(),),
        ).fetchone()
        if not row:
            return None
        return row["matric_no"], row["school_id"]


def get_balance(school_id: int, matric_no: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT balance FROM referral_credits WHERE school_id = ? AND matric_no = ?",
            (school_id, matric_no.upper()),
        ).fetchone()
        return int(row["balance"]) if row else 0


def add_credit(school_id: int, matric_no: str, amount: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO referral_credits(school_id, matric_no, balance, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(school_id, matric_no) DO UPDATE SET balance = balance + excluded.balance, updated_at = excluded.updated_at",
            (school_id, matric_no.upper(), amount, _now()),
        )


def consume_balance(school_id: int, matric_no: str, amount: int) -> None:
    if amount <= 0:
        return
    with get_conn() as conn:
        conn.execute(
            "UPDATE referral_credits SET balance = MAX(0, balance - ?), updated_at = ? "
            "WHERE school_id = ? AND matric_no = ?",
            (amount, _now(), school_id, matric_no.upper()),
        )


def quote(school_id: int, base_amount: int, matric_no: str, code: Optional[str] = None) -> dict:
    """Returns {amount, code_discount, credit_applied, code_owner_matric|None}.

    Rejects self-referral (code owner == current matric).
    """
    code_discount = 0
    code_owner_matric = None
    if code:
        owner = find_owner_matric_and_school(code)
        if owner:
            owner_matric, owner_school_id = owner
            if owner_school_id == school_id and owner_matric.upper() != matric_no.upper():
                code_discount = DISCOUNT_NGN
                code_owner_matric = owner_matric
    credit_balance = get_balance(school_id, matric_no)
    after_discount = max(0, base_amount - code_discount)
    credit_applied = min(credit_balance, after_discount)
    final_amount = after_discount - credit_applied
    return {
        "amount": final_amount,
        "code_discount": code_discount,
        "credit_applied": credit_applied,
        "code_owner_matric": code_owner_matric,
    }
