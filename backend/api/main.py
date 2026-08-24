"""SIWES Multi-Tenant Platform — FastAPI app."""

import asyncio
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import (
    APIRouter, Body, Depends, FastAPI, File, Form, HTTPException,
    Query, Request, Response, UploadFile, status,
)
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Load .env from project root and backend/
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from . import auth
from . import form_to_payload
from . import generation as generation_worker
from . import generation_logs as logs_repo
from . import orders as orders_repo
from . import paystack
from . import referrals as referrals_repo
from . import schools as schools_repo
from . import settings as platform_settings
from . import school_admin
from . import super_admin
from . import webhooks
from .config import PROJECT_ROOT, callback_url, public_base_url
from .db import init_db
from .orders import OrderStatus


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    platform_settings.seed_defaults()
    auth.seed_super_admin_from_env()
    (PROJECT_ROOT / "backend" / "outputs").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "backend" / "uploads").mkdir(parents=True, exist_ok=True)
    generation_worker.requeue_orphaned()

    purge_task = asyncio.create_task(_session_purge_loop())
    watchdog_task = asyncio.create_task(_watchdog_loop())
    try:
        yield
    finally:
        purge_task.cancel()
        watchdog_task.cancel()


async def _session_purge_loop():
    while True:
        try:
            auth.purge_expired_sessions()
        except Exception:
            pass
        await asyncio.sleep(60 * 60)


async def _watchdog_loop():
    while True:
        try:
            generation_worker.sweep_stuck_orders()
        except Exception:
            pass
        await asyncio.sleep(60 * 10)


app = FastAPI(title="SIWES Platform", lifespan=lifespan)


# ---- Static (assets like logos) ----
ASSETS_DIR = PROJECT_ROOT / "backend" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# Admin SPA mount is registered AFTER all /admin/api routes (see bottom of file)
ADMIN_DIST = PROJECT_ROOT / "admin" / "dist"


@app.get("/healthz")
def healthz():
    return {"ok": True, "now": datetime.now(timezone.utc).isoformat()}


@app.get("/admin", include_in_schema=False)
def admin_redirect():
    return RedirectResponse("/admin/")


# ============================================================
# Shared auth routes (super_admin + school_admin)
# ============================================================

@app.post("/admin/api/auth/login")
def login(request: Request, response: Response, payload: dict = Body(...)):
    ip = auth.client_ip(request)
    auth.rate_limit_check(ip)

    username = (payload.get("username") or "").strip().lower()
    pin = payload.get("pin") or ""
    if not username or not pin:
        raise HTTPException(status_code=400, detail="username and pin required")

    if username == "superadmin":
        if not auth.verify_super_admin_pin(pin):
            auth.rate_limit_record(ip)
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token, expires = auth.create_session(role="super_admin", school_admin_id=None, school_id=None, ip=ip)
        auth.rate_limit_clear(ip)
        auth.set_session_cookie(response, token, expires)
        return {"role": "super_admin"}

    admin = auth.verify_school_admin_credentials(username, pin)
    if not admin:
        auth.rate_limit_record(ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    school = schools_repo.get_school(admin["school_id"]) or {}
    if not school.get("active"):
        raise HTTPException(status_code=403, detail="School inactive")
    token, expires = auth.create_session(
        role="school_admin", school_admin_id=admin["id"], school_id=admin["school_id"], ip=ip,
    )
    auth.rate_limit_clear(ip)
    auth.set_session_cookie(response, token, expires)
    return {"role": "school_admin", "school_id": admin["school_id"], "school_slug": school.get("slug"), "display_name": admin.get("display_name") or admin["username"]}


@app.post("/admin/api/auth/logout")
def logout(response: Response, session: dict = Depends(auth.require_session)):
    auth.delete_session(session["token"])
    auth.clear_session_cookie(response)
    return {"ok": True}


@app.get("/admin/api/auth/me")
def me(session: dict = Depends(auth.require_session)):
    out = {"role": session["role"]}
    if session.get("school_id"):
        school = schools_repo.get_school(int(session["school_id"]))
        if school:
            out["school"] = {
                "id": school["id"],
                "slug": school["slug"],
                "name": school["name"],
                "full_name": school["full_name"],
            }
    if session.get("school_admin_id"):
        admin = schools_repo.get_school_admin(int(session["school_admin_id"]))
        if admin:
            out["admin"] = {"id": admin["id"], "username": admin["username"], "display_name": admin.get("display_name")}
    out["super_admin_set"] = auth.super_admin_exists()
    return out


@app.post("/admin/api/auth/change-pin")
def change_pin(payload: dict = Body(...), session: dict = Depends(auth.require_session)):
    old_pin = payload.get("old_pin") or ""
    new_pin = payload.get("new_pin") or ""
    if len(new_pin) < 4:
        raise HTTPException(status_code=400, detail="New PIN must be >= 4 chars")
    if session["role"] == "super_admin":
        if not auth.verify_super_admin_pin(old_pin):
            raise HTTPException(status_code=401, detail="Old PIN incorrect")
        auth.set_super_admin_pin(new_pin)
    else:
        admin = schools_repo.get_school_admin(int(session["school_admin_id"]))
        if not admin or not auth.verify_pin(old_pin, admin["pin_hash"]):
            raise HTTPException(status_code=401, detail="Old PIN incorrect")
        schools_repo.update_school_admin(admin["id"], pin_hash=auth.hash_pin(new_pin))
    return {"ok": True}


# Mount sub-routers
app.include_router(super_admin.router)
app.include_router(school_admin.router)
app.include_router(webhooks.router)

# Mount the admin SPA AFTER all /admin/api routes are registered, so the static
# mount doesn't shadow them.
if ADMIN_DIST.exists():
    app.mount("/admin", StaticFiles(directory=str(ADMIN_DIST), html=True), name="admin_spa")


# ============================================================
# Student-facing routes (per-school, slug-scoped)
# ============================================================

def _require_school(school_slug: str) -> dict:
    school = schools_repo.get_school_by_slug(school_slug)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school


def _school_logo_url(school: dict) -> Optional[str]:
    logo = school.get("logo_path")
    if not logo:
        return None
    abs_path = Path(logo) if os.path.isabs(logo) else PROJECT_ROOT / logo
    if not abs_path.exists():
        return None
    try:
        rel = abs_path.relative_to(ASSETS_DIR)
        return f"/assets/{rel.as_posix()}"
    except ValueError:
        return None


def _school_context(school: dict) -> dict:
    prices = schools_repo.get_school_prices(school["id"])
    config = schools_repo.get_school_config(school["id"])
    return {
        "school": school,
        "school_logo_url": _school_logo_url(school),
        "prices": prices,
        "config": config,
    }


@app.get("/", response_class=HTMLResponse)
def root_index(request: Request):
    schools = schools_repo.list_schools()
    return templates.TemplateResponse(request, "root.html", {"schools": schools})


@app.get("/{school_slug}", response_class=HTMLResponse)
def landing(school_slug: str, request: Request):
    school = _require_school(school_slug)
    ctx = _school_context(school)
    return templates.TemplateResponse(request, "landing.html", ctx)


@app.get("/{school_slug}/api/prices")
def api_prices(school_slug: str):
    school = _require_school(school_slug)
    return schools_repo.get_school_prices(school["id"])


@app.get("/{school_slug}/api/stats")
def api_stats(school_slug: str):
    school = _require_school(school_slug)
    rev = orders_repo.revenue_summary(school["id"])
    return {"orders_generated": rev["count"]}


@app.get("/{school_slug}/api/config")
def api_config(school_slug: str):
    school = _require_school(school_slug)
    cfg = schools_repo.get_school_config(school["id"])
    # Pull JSON-shaped fields out into parsed form for the form page
    def _parse(s: str, default):
        try:
            return json.loads(s)
        except Exception:
            return default
    return {
        "degrees": _parse(cfg.get("degrees", "[]"), []),
        "departments": _parse(cfg.get("departments", "[]"), []),
        "colleges": _parse(cfg.get("colleges", "[]"), []),
        "school": {"name": school["name"], "full_name": school["full_name"]},
    }


@app.get("/{school_slug}/api/referral/quote")
def api_referral_quote(
    school_slug: str,
    matric_no: str = Query(...),
    package: str = Query(...),
    express: bool = Query(False),
    code: Optional[str] = Query(None),
):
    school = _require_school(school_slug)
    prices = schools_repo.get_school_prices(school["id"])
    pkg = prices.get(package) or prices.get("basic")
    base = pkg["amount"]
    if express:
        base += prices.get("express_addon", {}).get("amount", 0)
    return referrals_repo.quote(school["id"], base, matric_no, code)


@app.get("/{school_slug}/orders/lookup", response_class=HTMLResponse)
def lookup_form(school_slug: str, request: Request):
    school = _require_school(school_slug)
    ctx = _school_context(school)
    return templates.TemplateResponse(request, "lookup.html", {"results": None, "error": None, **ctx})


@app.post("/{school_slug}/orders/lookup", response_class=HTMLResponse)
def lookup_submit(
    school_slug: str,
    request: Request,
    matric_no: str = Form(...),
    email: str = Form(...),
):
    school = _require_school(school_slug)
    ctx = _school_context(school)
    results = orders_repo.lookup_by_matric_and_email(school["id"], matric_no, email)
    return templates.TemplateResponse(
        request, "lookup.html",
        {"results": results, "error": None, **ctx},
    )


@app.post("/{school_slug}/orders/initiate")
async def initiate(
    school_slug: str,
    request: Request,
    payload: dict = Body(...),
):
    school = _require_school(school_slug)
    student_name = (payload.get("student_name") or "").strip()
    matric_no = (payload.get("matric_no") or "").strip().upper()
    email = (payload.get("email") or "").strip()
    package = (payload.get("package") or "basic").strip().lower()
    express = bool(payload.get("express"))
    referral_code = (payload.get("referral_code") or "").strip().upper() or None

    if not student_name or not matric_no or not email:
        raise HTTPException(status_code=400, detail="Missing student fields")

    prices = schools_repo.get_school_prices(school["id"])
    pkg_prices = prices.get(package) or prices.get("basic")
    base_amount = pkg_prices["amount"]
    if express:
        base_amount += prices.get("express_addon", {}).get("amount", 0)

    q = referrals_repo.quote(school["id"], base_amount, matric_no, referral_code)
    final_amount = q["amount"]

    # Idempotency: skip duplicate clicks
    existing = orders_repo.find_recent_pending(school["id"], matric_no, package, final_amount)
    if existing:
        return {
            "order_id": existing["id"],
            "amount": final_amount,
            "reference": existing.get("reference"),
            "form_token": existing.get("form_token"),
            "status_url": f"/{school_slug}/orders/{existing['id']}/status",
        }

    platform_amount, admin_amount = orders_repo.split_revenue(final_amount, int(school.get("platform_cut_pct") or 20))
    reference = paystack.new_reference()
    form_token = secrets.token_urlsafe(24)
    order_id = orders_repo.create_minimal_order(
        school_id=school["id"],
        student_name=student_name,
        matric_no=matric_no,
        email=email,
        package=package,
        amount=final_amount,
        platform_amount=platform_amount,
        admin_amount=admin_amount,
        express=express,
        reference=reference,
        form_token=form_token,
        referral_code_used=referral_code,
        referral_discount=q["code_discount"],
        referral_credit_applied=q["credit_applied"],
    )

    if final_amount <= 0:
        # Free order — skip Paystack, advance to awaiting_details
        orders_repo.transition_status(
            from_=OrderStatus.PENDING_PAYMENT.value,
            to=OrderStatus.AWAITING_DETAILS.value,
            order_id=order_id,
        )
        return {
            "order_id": order_id,
            "amount": final_amount,
            "form_token": form_token,
            "status_url": f"/{school_slug}/orders/{order_id}/status",
            "form_url": f"/{school_slug}/orders/{order_id}/form?token={form_token}",
        }

    secret = paystack.school_secret_key(school)
    if not secret:
        raise HTTPException(status_code=503, detail="Payment not configured for this school")

    try:
        result = await paystack.initialize_transaction(
            secret=secret,
            email=email,
            amount_kobo=final_amount * 100,
            reference=reference,
            callback_url=callback_url(school_slug, order_id, str(request.base_url)),
            metadata={"order_id": order_id, "school_slug": school_slug, "form_token": form_token},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Paystack error: {e}")

    return {
        "order_id": order_id,
        "amount": final_amount,
        "reference": reference,
        "authorization_url": result.get("data", {}).get("authorization_url"),
        "form_token": form_token,
        "status_url": f"/{school_slug}/orders/{order_id}/status",
    }


@app.get("/{school_slug}/orders/{order_id}/form", response_class=HTMLResponse)
def form_page(
    school_slug: str,
    order_id: int,
    request: Request,
    token: str = Query(...),
):
    school = _require_school(school_slug)
    order = orders_repo.get_order_scoped(order_id, school["id"])
    if not order:
        raise HTTPException(status_code=404, detail="Not found")
    if not orders_repo.verify_form_token(order_id, token):
        raise HTTPException(status_code=403, detail="Invalid token")
    if order["status"] not in (OrderStatus.AWAITING_DETAILS.value, OrderStatus.PENDING_PAYMENT.value):
        return RedirectResponse(f"/{school_slug}/orders/{order_id}/status")

    ctx = _school_context(school)
    try:
        payload = json.loads(order["payload_json"])
    except Exception:
        payload = {}
    return templates.TemplateResponse(
        request, "form.html",
        {
            "order": order,
            "payload": payload,
            "form_token": token,
            "config_parsed": {
                "degrees": json.loads(ctx["config"].get("degrees", "[]") or "[]"),
                "departments": json.loads(ctx["config"].get("departments", "[]") or "[]"),
                "colleges": json.loads(ctx["config"].get("colleges", "[]") or "[]"),
            },
            **ctx,
        },
    )


@app.post("/{school_slug}/orders/{order_id}/complete")
async def complete_form(
    school_slug: str,
    order_id: int,
    request: Request,
    token: str = Query(...),
):
    school = _require_school(school_slug)
    order = orders_repo.get_order_scoped(order_id, school["id"])
    if not order:
        raise HTTPException(status_code=404, detail="Not found")
    if not orders_repo.verify_form_token(order_id, token):
        raise HTTPException(status_code=403, detail="Invalid token")

    form = await request.form()
    form_dict = {k: form.get(k) for k in form}
    files = {k: form.get(k) for k in form if hasattr(form.get(k), "filename")}

    image_uploads = form.getlist("image_file") if hasattr(form, "getlist") else []
    image_chapters = form.getlist("image_chapter") if hasattr(form, "getlist") else []
    image_descriptions = form.getlist("image_description") if hasattr(form, "getlist") else []

    payload = form_to_payload.build_payload(
        form_dict,
        files,
        order_id=order_id,
        project_root=PROJECT_ROOT,
        image_uploads=image_uploads,
        image_chapters=image_chapters,
        image_descriptions=image_descriptions,
    )
    # Stamp order info from server (don't trust the form)
    payload["order"] = {
        "package": order["package"],
        "amount": order["amount"],
        "express": bool(order["express"]),
    }
    orders_repo.update_payload(order_id, payload)

    # Move from awaiting_details (or pending_payment for free orders) → generating
    advanced = orders_repo.transition_status(
        from_=[OrderStatus.AWAITING_DETAILS.value, OrderStatus.PENDING_PAYMENT.value],
        to=OrderStatus.GENERATING.value,
        order_id=order_id,
    )
    if not advanced:
        raise HTTPException(status_code=409, detail="Order is not awaiting details")
    asyncio.create_task(generation_worker.generate_for_order(order_id))
    return RedirectResponse(f"/{school_slug}/orders/{order_id}/status", status_code=303)


@app.get("/{school_slug}/orders/{order_id}/status", response_class=HTMLResponse)
def status_page(school_slug: str, order_id: int, request: Request):
    school = _require_school(school_slug)
    order = orders_repo.get_order_scoped(order_id, school["id"])
    if not order:
        raise HTTPException(status_code=404, detail="Not found")
    ctx = _school_context(school)
    return templates.TemplateResponse(
        request, "status.html",
        {"order": order, **ctx},
    )


@app.get("/{school_slug}/orders/{order_id}/status.json")
def status_json(school_slug: str, order_id: int):
    school = _require_school(school_slug)
    order = orders_repo.get_order_scoped(order_id, school["id"])
    if not order:
        raise HTTPException(status_code=404, detail="Not found")
    logs = logs_repo.for_order(order_id)
    milestones = [l["message"].split(":", 1)[1] for l in logs if l["message"].startswith("milestone:")]
    return {
        "id": order["id"],
        "status": order["status"],
        "package": order["package"],
        "milestones": milestones,
        "referral_code": order.get("referral_code"),
        "has_docx": bool(order.get("docx_path")),
        "has_pptx": bool(order.get("pptx_path")),
    }


@app.get("/{school_slug}/download/{order_id}/{file_type}")
def download(
    school_slug: str,
    order_id: int,
    file_type: str,
    token: Optional[str] = Query(None),
    request: Request = None,
):
    school = _require_school(school_slug)
    order = orders_repo.get_order_scoped(order_id, school["id"])
    if not order:
        raise HTTPException(status_code=404, detail="Not found")

    # Token grants access; otherwise the school admin's session does
    has_access = False
    if token and orders_repo.verify_form_token(order_id, token):
        has_access = True
    else:
        cookie = request.cookies.get(auth.SESSION_COOKIE) if request else None
        sess = auth.get_session_row(cookie)
        if sess and (sess["role"] == "super_admin" or int(sess.get("school_id") or 0) == school["id"]):
            has_access = True
    if not has_access:
        raise HTTPException(status_code=403, detail="Forbidden")

    if file_type == "docx":
        path = order.get("docx_path")
    elif file_type == "pptx":
        path = order.get("pptx_path")
    else:
        raise HTTPException(status_code=400, detail="Unknown file type")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="File not generated yet")
    return FileResponse(path, filename=Path(path).name)
