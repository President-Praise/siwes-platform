"""Per-order generation event log."""

from datetime import datetime, timezone

from .db import get_conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(order_id: int, level: str, message: str, duration_ms: int | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO generation_logs(order_id, timestamp, level, message, duration_ms) VALUES (?, ?, ?, ?, ?)",
            (order_id, _now(), level, message[:2000], duration_ms),
        )


def for_order(order_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM generation_logs WHERE order_id = ? ORDER BY id ASC",
            (order_id,),
        ).fetchall()
        return [dict(r) for r in rows]
