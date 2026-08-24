"""Background generation worker. School-config-aware."""

import asyncio
import contextvars
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from . import generation_logs as logs_repo
from . import orders as orders_repo
from . import referrals as referrals_repo
from . import schools as schools_repo
from .config import PROJECT_ROOT
from .orders import OrderStatus

MAX_CONCURRENT_GENERATIONS = 6
STUCK_AFTER_MINUTES = 20

_pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_GENERATIONS, thread_name_prefix="siwes-gen")


async def generate_for_order(order_id: int) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_pool, _sync_generate, order_id)


def _sync_generate(order_id: int) -> None:
    started = time.time()
    order = orders_repo.get_order(order_id)
    if not order:
        return
    if order["status"] != OrderStatus.GENERATING.value:
        return

    try:
        payload = json.loads(order["payload_json"])
    except Exception as e:
        orders_repo.mark_failed(order_id, f"payload_json invalid: {e}")
        logs_repo.log(order_id, "error", f"payload_json invalid: {e}")
        return

    school_id = order["school_id"]
    school = schools_repo.get_school(school_id) or {}
    school_config = schools_repo.school_for_payload(school_id)

    def on_progress(stage: str):
        logs_repo.log(order_id, "info", f"milestone:{stage}")

    outputs_dir = PROJECT_ROOT / "backend" / "outputs" / str(order_id)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    try:
        from backend.services.report_generator import generate_report
        from backend.services.ppt_generator import generate_pptx
    except ImportError:
        # Allow running from inside backend/ as well
        from services.report_generator import generate_report  # type: ignore
        from services.ppt_generator import generate_pptx  # type: ignore

    force_stub = bool(order.get("test_mode"))

    try:
        logs_repo.log(order_id, "info", "generation_started")

        docx_path = generate_report(
            payload,
            str(outputs_dir),
            project_root=PROJECT_ROOT,
            on_progress=on_progress,
            force_stub=force_stub,
            school_config=school_config,
        )

        pptx_path = None
        package = (order.get("package") or "").lower()
        if package in ("standard", "premium"):
            pptx_path = generate_pptx(
                payload,
                str(outputs_dir),
                project_root=PROJECT_ROOT,
                on_progress=on_progress,
                school_config=school_config,
            )

        orders_repo.mark_generated(order_id, docx_path, pptx_path)
        duration_ms = int((time.time() - started) * 1000)
        logs_repo.log(order_id, "info", "generation_completed", duration_ms=duration_ms)

        # Assign referral code on first successful generation (non-test orders)
        if not force_stub:
            prefix = school.get("referral_prefix") or "REF"
            referrals_repo.assign_code_if_missing(order_id, prefix)

            # Credit the referrer if a code was used
            code_used = order.get("referral_code_used")
            credit = referrals_repo.DISCOUNT_NGN
            if code_used:
                owner = referrals_repo.find_owner_matric_and_school(code_used)
                if owner and owner[1] == school_id:
                    referrals_repo.add_credit(school_id, owner[0], credit)

            # Deduct any consumed credit
            credit_applied = int(order.get("referral_credit_applied") or 0)
            if credit_applied > 0:
                referrals_repo.consume_balance(school_id, order["matric_no"], credit_applied)

    except Exception as e:
        orders_repo.mark_failed(order_id, str(e))
        logs_repo.log(order_id, "error", f"generation_failed: {e}")


def requeue_orphaned() -> None:
    """On startup, kick the worker for any orders stuck in 'generating'."""
    rows = orders_repo.all_generating()
    for r in rows:
        try:
            asyncio.get_event_loop().create_task(generate_for_order(r["id"]))
        except RuntimeError:
            # No running loop yet — schedule via sync path
            _pool.submit(_sync_generate, r["id"])


def sweep_stuck_orders() -> None:
    """Mark orders stuck in 'generating' for > STUCK_AFTER_MINUTES as failed."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=STUCK_AFTER_MINUTES)).isoformat()
    rows = orders_repo.all_generating()
    for r in rows:
        if r["created_at"] < cutoff:
            orders_repo.mark_failed(r["id"], "stuck > 20 min — watchdog timeout")
            logs_repo.log(r["id"], "error", "watchdog_timeout")
