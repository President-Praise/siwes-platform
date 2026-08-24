"""Super admin API routes. Platform-wide visibility and control."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile

from . import auth
from . import orders as orders_repo
from . import schools as schools_repo
from . import settings as settings_repo
from .config import PROJECT_ROOT

router = APIRouter(prefix="/admin/api/super", tags=["super_admin"])


@router.get("/dashboard")
def dashboard(session: dict = Depends(auth.require_super_admin)):
    schools = schools_repo.list_schools(include_inactive=True)
    revenue_total = orders_repo.revenue_summary()
    per_school = orders_repo.revenue_by_school()
    revenue_30d = orders_repo.revenue_by_day(days=30)
    return {
        "schools": schools,
        "schools_active": sum(1 for s in schools if s["active"]),
        "totals": revenue_total,
        "per_school": per_school,
        "revenue_by_day": revenue_30d,
    }


@router.get("/schools")
def list_schools(session: dict = Depends(auth.require_super_admin)):
    return schools_repo.list_schools(include_inactive=True)


@router.post("/schools")
def create_school(
    payload: dict = Body(...),
    session: dict = Depends(auth.require_super_admin),
):
    required = ["slug", "name", "full_name", "referral_prefix"]
    for k in required:
        if not (payload.get(k) or "").strip():
            raise HTTPException(status_code=400, detail=f"Missing field: {k}")
    slug = payload["slug"].strip().lower()
    existing = schools_repo.get_school_by_slug(slug)
    if existing:
        raise HTTPException(status_code=409, detail="Slug already in use")

    school_id = schools_repo.create_school(
        slug=slug,
        name=payload["name"].strip(),
        full_name=payload["full_name"].strip(),
        referral_prefix=payload["referral_prefix"].strip().upper(),
        logo_path=payload.get("logo_path"),
        paystack_secret_key=payload.get("paystack_secret_key") or None,
        paystack_public_key=payload.get("paystack_public_key") or None,
        platform_cut_pct=int(payload.get("platform_cut_pct", 20)),
    )
    return {"id": school_id, "school": schools_repo.get_school(school_id)}


@router.get("/schools/{school_id}")
def get_school(school_id: int, session: dict = Depends(auth.require_super_admin)):
    school = schools_repo.get_school(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "school": school,
        "config": schools_repo.get_school_config(school_id),
        "prices": schools_repo.get_school_prices(school_id),
        "admins": schools_repo.list_school_admins(school_id),
        "revenue": orders_repo.revenue_summary(school_id),
    }


@router.put("/schools/{school_id}")
def update_school(
    school_id: int,
    payload: dict = Body(...),
    session: dict = Depends(auth.require_super_admin),
):
    school = schools_repo.get_school(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Not found")
    allowed = {"name", "full_name", "slug", "referral_prefix", "platform_cut_pct",
               "paystack_secret_key", "paystack_public_key", "active", "logo_path"}
    fields = {k: v for k, v in payload.items() if k in allowed}
    if "platform_cut_pct" in fields:
        fields["platform_cut_pct"] = int(fields["platform_cut_pct"])
    if "active" in fields:
        fields["active"] = int(bool(fields["active"]))
    if "referral_prefix" in fields and fields["referral_prefix"]:
        fields["referral_prefix"] = str(fields["referral_prefix"]).upper()
    schools_repo.update_school(school_id, **fields)
    return {"school": schools_repo.get_school(school_id)}


@router.post("/schools/{school_id}/logo")
async def upload_school_logo(
    school_id: int,
    file: UploadFile = File(...),
    session: dict = Depends(auth.require_super_admin),
):
    return _save_logo(school_id, file)


def _save_logo(school_id: int, file: UploadFile) -> dict:
    school = schools_repo.get_school(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
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


@router.get("/schools/{school_id}/admins")
def list_admins(school_id: int, session: dict = Depends(auth.require_super_admin)):
    return schools_repo.list_school_admins(school_id)


@router.post("/schools/{school_id}/admins")
def create_admin(
    school_id: int,
    payload: dict = Body(...),
    session: dict = Depends(auth.require_super_admin),
):
    username = (payload.get("username") or "").strip().lower()
    pin = payload.get("pin") or ""
    if not username or len(pin) < 4:
        raise HTTPException(status_code=400, detail="username and PIN (>=4 chars) required")
    admin_id = schools_repo.create_school_admin(
        school_id, username, auth.hash_pin(pin), payload.get("display_name") or None
    )
    return {"id": admin_id}


@router.put("/admins/{admin_id}")
def update_admin(
    admin_id: int,
    payload: dict = Body(...),
    session: dict = Depends(auth.require_super_admin),
):
    fields = {}
    if "display_name" in payload:
        fields["display_name"] = payload["display_name"]
    if "active" in payload:
        fields["active"] = int(bool(payload["active"]))
    if payload.get("pin"):
        if len(payload["pin"]) < 4:
            raise HTTPException(status_code=400, detail="PIN must be >= 4 chars")
        fields["pin_hash"] = auth.hash_pin(payload["pin"])
    schools_repo.update_school_admin(admin_id, **fields)
    return {"ok": True}


@router.get("/orders")
def all_orders(
    school_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    session: dict = Depends(auth.require_super_admin),
):
    return orders_repo.list_orders(
        school_id=school_id, status=status, q=q, limit=limit, offset=offset
    )


@router.get("/revenue")
def revenue(days: int = Query(30, ge=1, le=365), session: dict = Depends(auth.require_super_admin)):
    return {
        "totals": orders_repo.revenue_summary(),
        "per_school": orders_repo.revenue_by_school(),
        "by_day": orders_repo.revenue_by_day(days=days),
    }
