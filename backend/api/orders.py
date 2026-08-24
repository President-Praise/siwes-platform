"""Order CRUD + state machine. School-scoped."""

import hmac
import json
import secrets
from datetime import datetime, timezone, timedelta
from enum import StrEnum
from typing import Optional

from .db import get_conn


class OrderStatus(StrEnum):
    PENDING = "pending"
    PENDING_PAYMENT = "pending_payment"
    AWAITING_DETAILS = "awaiting_details"
    GENERATING = "generating"
    GENERATED = "generated"
    FAILED = "failed"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(matric: str) -> str:
    return (matric or "").strip().upper()


def split_revenue(amount: int, platform_cut_pct: int) -> tuple[int, int]:
    platform = int(amount * platform_cut_pct / 100)
    admin = amount - platform
    return platform, admin


def create_minimal_order(
    *,
    school_id: int,
    student_name: str,
    matric_no: str,
    email: str,
    package: str,
    amount: int,
    platform_amount: int,
    admin_amount: int,
    express: bool,
    reference: str | None,
    form_token: str | None,
    referral_code_used: str | None = None,
    referral_discount: int = 0,
    referral_credit_applied: int = 0,
    test_mode: bool = False,
    status: str = OrderStatus.PENDING_PAYMENT.value,
) -> int:
    stub_payload = {
        "student": {"name": student_name, "matric_no": _norm(matric_no), "email": email},
        "order": {"package": package, "amount": amount, "express": express},
    }
    priority = 10 if express else 0
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO orders(school_id, created_at, matric_no, student_name, student_email, "
            "package, amount, platform_amount, admin_amount, express, priority, payload_json, "
            "status, reference, form_token, referral_code_used, referral_discount, "
            "referral_credit_applied, test_mode) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                school_id, _now(), _norm(matric_no), student_name, email,
                package, amount, platform_amount, admin_amount, int(express), priority,
                json.dumps(stub_payload), status, reference, form_token,
                referral_code_used, referral_discount, referral_credit_applied, int(test_mode),
            ),
        )
        return cur.lastrowid


def verify_form_token(order_id: int, token: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT form_token FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row or not row["form_token"]:
            return False
        return hmac.compare_digest(row["form_token"], token or "")


def transition_status(*, from_: str | list[str], to: str, order_id: int | None = None, reference: str | None = None) -> bool:
    """Atomic CAS. Returns True if a row was updated."""
    if isinstance(from_, str):
        from_list = [from_]
    else:
        from_list = list(from_)
    placeholders = ",".join("?" * len(from_list))
    args = [to] + from_list
    if order_id is not None:
        sql = f"UPDATE orders SET status = ? WHERE status IN ({placeholders}) AND id = ?"
        args.append(order_id)
    elif reference is not None:
        sql = f"UPDATE orders SET status = ? WHERE status IN ({placeholders}) AND reference = ?"
        args.append(reference)
    else:
        return False
    with get_conn() as conn:
        cur = conn.execute(sql, args)
        return cur.rowcount > 0


def update_payload(order_id: int, payload: dict) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE orders SET payload_json = ? WHERE id = ?", (json.dumps(payload), order_id))


def mark_generated(order_id: int, docx_path: str, pptx_path: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE orders SET status = ?, docx_path = ?, pptx_path = ?, error_message = NULL WHERE id = ?",
            (OrderStatus.GENERATED.value, docx_path, pptx_path, order_id),
        )


def mark_failed(order_id: int, error: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE orders SET status = ?, error_message = ? WHERE id = ?",
            (OrderStatus.FAILED.value, error[:2000], order_id),
        )


def mark_delivered(order_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE orders SET delivered_at = ? WHERE id = ?", (_now(), order_id))


def mark_printed(order_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE orders SET printed_at = ? WHERE id = ?", (_now(), order_id))


def get_order(order_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return dict(row) if row else None


def get_order_scoped(order_id: int, school_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE id = ? AND school_id = ?",
            (order_id, school_id),
        ).fetchone()
        return dict(row) if row else None


def list_orders(
    *,
    school_id: int | None = None,
    status: str | None = None,
    statuses: list[str] | None = None,
    q: str | None = None,
    package: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    where = []
    args: list = []
    if school_id is not None:
        where.append("school_id = ?")
        args.append(school_id)
    if status:
        where.append("status = ?")
        args.append(status)
    if statuses:
        ph = ",".join("?" * len(statuses))
        where.append(f"status IN ({ph})")
        args.extend(statuses)
    if package:
        where.append("package = ?")
        args.append(package)
    if q:
        where.append("(student_name LIKE ? OR matric_no LIKE ? OR student_email LIKE ?)")
        args.extend([f"%{q}%", f"%{q.upper()}%", f"%{q}%"])
    if date_from:
        where.append("created_at >= ?")
        args.append(date_from)
    if date_to:
        where.append("created_at <= ?")
        args.append(date_to)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    args.extend([limit, offset])
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM orders {where_sql} ORDER BY priority DESC, id DESC LIMIT ? OFFSET ?",
            args,
        ).fetchall()
        return [dict(r) for r in rows]


def lookup_by_matric_and_email(school_id: int, matric_no: str, email: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE school_id = ? AND matric_no = ? AND LOWER(student_email) = LOWER(?) "
            "ORDER BY id DESC LIMIT 20",
            (school_id, _norm(matric_no), email.strip()),
        ).fetchall()
        return [dict(r) for r in rows]


def by_matric(school_id: int, matric_no: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE school_id = ? AND matric_no = ? ORDER BY id DESC",
            (school_id, _norm(matric_no)),
        ).fetchall()
        return [dict(r) for r in rows]


def print_queue(school_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE school_id = ? AND status = 'generated' AND printed_at IS NULL "
            "ORDER BY priority DESC, id ASC",
            (school_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def find_recent_pending(school_id: int, matric_no: str, package: str, amount: int, within_seconds: int = 60) -> Optional[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=within_seconds)).isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE school_id = ? AND matric_no = ? AND package = ? AND amount = ? "
            "AND status = 'pending_payment' AND created_at >= ? ORDER BY id DESC LIMIT 1",
            (school_id, _norm(matric_no), package, amount, cutoff),
        ).fetchone()
        return dict(row) if row else None


def revenue_summary(school_id: int | None = None) -> dict:
    """Returns gross/platform/admin totals for generated orders (excluding test_mode)."""
    where = ["status = 'generated'", "test_mode = 0"]
    args: list = []
    if school_id is not None:
        where.append("school_id = ?")
        args.append(school_id)
    sql = (
        "SELECT COALESCE(SUM(amount),0) AS gross, COALESCE(SUM(platform_amount),0) AS platform, "
        "COALESCE(SUM(admin_amount),0) AS admin, COUNT(*) AS count FROM orders "
        f"WHERE {' AND '.join(where)}"
    )
    with get_conn() as conn:
        row = conn.execute(sql, args).fetchone()
        return {"gross": row["gross"], "platform": row["platform"], "admin": row["admin"], "count": row["count"]}


def revenue_by_day(school_id: int | None = None, days: int = 30) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    where = ["status = 'generated'", "test_mode = 0", "created_at >= ?"]
    args: list = [since]
    if school_id is not None:
        where.append("school_id = ?")
        args.append(school_id)
    sql = (
        "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS orders, "
        "COALESCE(SUM(amount), 0) AS revenue, COALESCE(SUM(platform_amount), 0) AS platform "
        f"FROM orders WHERE {' AND '.join(where)} GROUP BY day ORDER BY day ASC"
    )
    with get_conn() as conn:
        rows = conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]


def revenue_by_school() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT s.id AS school_id, s.name, s.slug, "
            "COALESCE(SUM(o.amount), 0) AS gross, "
            "COALESCE(SUM(o.platform_amount), 0) AS platform, "
            "COALESCE(SUM(o.admin_amount), 0) AS admin, "
            "COUNT(o.id) AS order_count "
            "FROM schools s LEFT JOIN orders o "
            "  ON o.school_id = s.id AND o.status = 'generated' AND o.test_mode = 0 "
            "GROUP BY s.id ORDER BY platform DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_notes(order_id: int, notes: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE orders SET notes = ? WHERE id = ?", (notes, order_id))


def all_generating() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE status = 'generating' ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def assign_referral_code(order_id: int, code: str) -> bool:
    """Returns True if code was assigned, False if order already had one or row missing."""
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE orders SET referral_code = ? WHERE id = ? AND referral_code IS NULL",
            (code, order_id),
        )
        return cur.rowcount > 0
