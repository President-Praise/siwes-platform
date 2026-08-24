"""Paystack webhook handling."""

from fastapi import APIRouter, HTTPException, Request

from . import orders as orders_repo
from . import paystack
from . import schools as schools_repo
from .orders import OrderStatus

router = APIRouter()


@router.post("/webhook/paystack/{school_slug}")
async def paystack_webhook(school_slug: str, request: Request):
    school = schools_repo.get_school_by_slug(school_slug)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    secret = paystack.school_secret_key(school)
    if not paystack.verify_signature(body, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if event.get("event") == "charge.success":
        data = event.get("data", {})
        reference = data.get("reference")
        if reference:
            orders_repo.transition_status(
                from_=OrderStatus.PENDING_PAYMENT.value,
                to=OrderStatus.AWAITING_DETAILS.value,
                reference=reference,
            )
    return {"ok": True}
