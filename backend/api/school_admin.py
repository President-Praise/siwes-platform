"""School admin API routes. ALL queries filter by school_id — data isolation is non-negotiable.

Super admin may act as a school admin by passing ?school_id= on each request.
"""

import asyncio
import csv
import io
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from . import auth
from . import generation as generation_worker
from . import generation_logs as logs_repo
from . import orders as orders_repo
from . import schools as schools_repo
from .config import PROJECT_ROOT
from .orders import OrderStatus

router = APIRouter(prefix="/admin/api/school", tags=["school_admin"])


def _ctx(request: Request, session: dict = Depends(auth.require_school_admin)) -> tuple[dict, int]:
    school_id = auth.resolved_school_id(session, request)
    school = schools_repo.get_school(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return session, school_id


@router.get("/dashboard")
def dashboard(request: Request, session_school=Depends(_ctx)):
    _, school_id = session_school
    rev = orders_repo.revenue_summary(school_id)
    by_day = orders_repo.revenue_by_day(school_id=school_id, days=30)
    recent = orders_repo.list_orders(school_id=school_id, limit=10)
    return {
        "school": schools_repo.get_school(school_id),
        "revenue": rev,
        "by_day": by_day,
        "recent": recent,
    }


@router.get("/orders")
def list_orders(
    request: Request,
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    package: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    session_school=Depends(_ctx),
):
    _, school_id = session_school
    return orders_repo.list_orders(
        school_id=school_id, status=status, q=q, package=package,
        date_from=date_from, date_to=date_to, limit=limit, offset=offset,
    )


@router.get("/orders/{order_id}")
def order_detail(order_id: int, request: Request, session_school=Depends(_ctx)):
    _, school_id = session_school
    order = orders_repo.get_order_scoped(order_id, school_id)
    if not order:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        payload = json.loads(order["payload_json"])
    except Exception:
        payload = None
    return {
        "order": order,
        "payload": payload,
        "logs": logs_repo.for_order(order_id),
    }


@router.post("/orders/{order_id}/deliver")
def deliver(order_id: int, request: Request, session_school=Depends(_ctx)):
    _, school_id = session_school
    if not orders_repo.get_order_scoped(order_id, school_id):
        raise HTTPException(status_code=404, detail="Not found")
    orders_repo.mark_delivered(order_id)
    return {"ok": True}


@router.post("/orders/{order_id}/mark-printed")
def mark_printed(order_id: int, request: Request, session_school=Depends(_ctx)):
    _, school_id = session_school
    if not orders_repo.get_order_scoped(order_id, school_id):
        raise HTTPException(status_code=404, detail="Not found")
    orders_repo.mark_printed(order_id)
    return {"ok": True}


@router.post("/orders/{order_id}/notes")
def update_notes(
    order_id: int,
    request: Request,
    payload: dict = Body(...),
    session_school=Depends(_ctx),
):
    _, school_id = session_school
    if not orders_repo.get_order_scoped(order_id, school_id):
        raise HTTPException(status_code=404, detail="Not found")
    orders_repo.update_notes(order_id, (payload.get("notes") or "")[:5000])
    return {"ok": True}


@router.post("/orders/{order_id}/retry")
async def retry_order(order_id: int, request: Request, session_school=Depends(_ctx)):
    _, school_id = session_school
    order = orders_repo.get_order_scoped(order_id, school_id)
    if not order:
        raise HTTPException(status_code=404, detail="Not found")
    changed = orders_repo.transition_status(
        from_=OrderStatus.FAILED.value, to=OrderStatus.GENERATING.value, order_id=order_id
    )
    if not changed:
        raise HTTPException(status_code=409, detail="Not in failed state")
    asyncio.create_task(generation_worker.generate_for_order(order_id))
    return {"ok": True}


@router.get("/students")
def students(request: Request, session_school=Depends(_ctx)):
    _, school_id = session_school
    rows = orders_repo.list_orders(school_id=school_id, limit=500)
    seen: dict[str, dict] = {}
    for r in rows:
        m = r["matric_no"]
        if m not in seen:
            seen[m] = {
                "matric_no": m,
                "student_name": r["student_name"],
                "email": r["student_email"],
                "order_count": 0,
                "total_spent": 0,
                "last_at": r["created_at"],
            }
        seen[m]["order_count"] += 1
        seen[m]["total_spent"] += int(r.get("amount") or 0)
        if r["created_at"] > seen[m]["last_at"]:
            seen[m]["last_at"] = r["created_at"]
    return list(seen.values())


@router.get("/analytics")
def analytics(request: Request, days: int = Query(30, ge=1, le=365), session_school=Depends(_ctx)):
    _, school_id = session_school
    return {
        "revenue": orders_repo.revenue_summary(school_id),
        "by_day": orders_repo.revenue_by_day(school_id=school_id, days=days),
    }


@router.get("/settings")
def get_settings(request: Request, session_school=Depends(_ctx)):
    _, school_id = session_school
    school = schools_repo.get_school(school_id)
    return {
        "school": school,
        "config": schools_repo.get_school_config(school_id),
        "prices": schools_repo.get_school_prices(school_id),
    }


@router.put("/settings")
def update_settings(
    request: Request,
    payload: dict = Body(...),
    session_school=Depends(_ctx),
):
    _, school_id = session_school
    school_fields = {}
    for k in ("name", "full_name"):
        if k in payload:
            school_fields[k] = payload[k]
    if school_fields:
        schools_repo.update_school(school_id, **school_fields)

    config_updates = payload.get("config") or {}
    if config_updates:
        # Normalize JSON-shaped fields
        for k, v in list(config_updates.items()):
            if isinstance(v, (list, dict)):
                config_updates[k] = json.dumps(v)
            else:
                config_updates[k] = str(v)
        schools_repo.update_school_config_bulk(school_id, config_updates)

    return {"ok": True, "config": schools_repo.get_school_config(school_id)}


@router.put("/prices")
def update_prices(
    request: Request,
    payload: dict = Body(...),
    session_school=Depends(_ctx),
):
    _, school_id = session_school
    prices = payload.get("prices") or {}
    schools_repo.update_school_prices(school_id, prices)
    return {"prices": schools_repo.get_school_prices(school_id)}


@router.post("/logo")
async def upload_logo(
    request: Request,
    file: UploadFile = File(...),
    session_school=Depends(_ctx),
):
    _, school_id = session_school
    school = schools_repo.get_school(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Not found")
    raw = file.file.read()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Logo must be under 2 MB")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg"):
        raise HTTPException(status_code=400, detail="Only PNG or JPG allowed")
    out_dir = PROJECT_ROOT / "backend" / "assets" / "schools" / school["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"logo{suffix}"
    with open(out_path, "wb") as f:
        f.write(raw)
    rel = str(out_path.relative_to(PROJECT_ROOT))
    schools_repo.update_school(school_id, logo_path=rel)
    return {"logo_path": rel}


@router.get("/print-queue")
def print_queue(request: Request, session_school=Depends(_ctx)):
    _, school_id = session_school
    return orders_repo.print_queue(school_id)


@router.get("/export")
def export_csv(request: Request, session_school=Depends(_ctx)):
    _, school_id = session_school
    rows = orders_repo.list_orders(school_id=school_id, limit=10000)
    buf = io.StringIO()
    fieldnames = [
        "id", "created_at", "status", "matric_no", "student_name", "student_email",
        "package", "amount", "platform_amount", "admin_amount", "express",
        "referral_code_used", "referral_discount", "referral_code", "delivered_at", "printed_at",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="orders.csv"'},
    )
